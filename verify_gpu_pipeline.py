"""GPU pipeline-refresh verification + micro-benchmark (v13.0.0).

Validates that the zero-copy upload + input-normalize pass introduced in the
13.0.0 pipeline refresh produces output that is *pixel-identical* to the old
`pygame.image.tobytes(surface, "RGBA", True)` path, and reports the CPU-side
upload cost saved.

Run:  ./venv/bin/python verify_gpu_pipeline.py

The correctness check needs a creatable OpenGL context (uses a standalone
context purely for offscreen readback — the game itself uses the shared
Pygame context). If no GL context is available, that check is skipped with a
notice; the CPU benchmark always runs.

Exit code is non-zero if the correctness check runs and fails.
"""

import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((64, 64))

W, H = 2560, 1440


def _make_surface(w, h):
    """A 32-bit surface matching the game's offscreen render target."""
    return pygame.Surface((w, h), depth=32)


def benchmark_upload(n=100):
    """Compare the old tobytes() conversion against the zero-copy buffer view."""
    s = _make_surface(W, H)

    def bench(fn):
        fn()  # warmup
        t = time.perf_counter()
        for _ in range(n):
            fn()
        return (time.perf_counter() - t) / n * 1000.0

    old_ms = bench(lambda: pygame.image.tobytes(s, "RGBA", True))
    new_ms = bench(lambda: memoryview(s.get_buffer()))  # zero-copy access
    print("== CPU upload-step micro-benchmark (%dx%d, %d iters) ==" % (W, H, n))
    print("  old  tobytes(RGBA, flip): %7.3f ms/frame" % old_ms)
    print("  new  get_buffer (0-copy): %7.3f ms/frame" % new_ms)
    if new_ms > 0:
        print("  speedup:                  %7.1fx  (saves ~%.1f ms/frame)"
              % (old_ms / new_ms, old_ms - new_ms))
    print()


def verify_correctness():
    """Assert normalize-pass output == old tobytes path, pixel-for-pixel."""
    try:
        import moderngl
        from gpu_renderer import ShaderPass, FBOPool, NORMALIZE_FRAG
    except ImportError as e:
        print("[skip] correctness check — moderngl unavailable: %s" % e)
        return True

    try:
        ctx = moderngl.create_standalone_context()
    except Exception as e:
        print("[skip] correctness check — no GL context here: %s" % e)
        return True

    w, h = 200, 120
    surf = _make_surface(w, h)
    surf.fill((0, 0, 0))
    # Asymmetric 4-corner pattern exercises BOTH orientation and channel order.
    surf.fill((255, 0, 0), (0, 0, 40, 30))            # top-left RED
    surf.fill((0, 255, 0), (w - 40, 0, 40, 30))       # top-right GREEN
    surf.fill((0, 0, 255), (0, h - 30, 40, 30))       # bottom-left BLUE
    surf.fill((255, 255, 0), (w - 40, h - 30, 40, 30))  # bottom-right YELLOW

    def readback(tex):
        return ctx.framebuffer(color_attachments=[tex]).read(components=4)

    old_tex = ctx.texture((w, h), 4)
    old_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    old_tex.write(pygame.image.tobytes(surf, "RGBA", True))
    old = readback(old_tex)

    pool = FBOPool(ctx)
    norm = ShaderPass(ctx, NORMALIZE_FRAG)
    in_tex = ctx.texture((w, h), 4)
    in_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    in_tex.write(surf.get_buffer())
    _, ntex = norm.apply(in_tex, pool, norm._vao, w, h)
    new = readback(ntex)

    diff = sum(1 for k in range(0, len(old), 4) if old[k:k + 3] != new[k:k + 3])
    print("== Correctness: normalize pass vs old tobytes path ==")
    print("  RGB pixels differing: %d of %d" % (diff, w * h))
    ok = diff == 0
    print("  RESULT: %s" % ("PASS (pixel-identical)" if ok else "FAIL"))
    print()
    return ok


def verify_clear_removal():
    """Assert skipping the per-pass FBO clear is byte-identical for an opaque
    pass, even with blend enabled and the target FBO pre-dirtied (v13.0.0)."""
    try:
        import moderngl
        from gpu_renderer import ShaderPass, FBOPool, NORMALIZE_FRAG
    except ImportError as e:
        print("[skip] clear-removal check — moderngl unavailable: %s" % e)
        return True
    try:
        ctx = moderngl.create_standalone_context()
    except Exception as e:
        print("[skip] clear-removal check — no GL context here: %s" % e)
        return True

    w, h = 128, 96
    surf = _make_surface(w, h)
    surf.fill((0, 0, 0))
    surf.fill((200, 30, 40), (0, 0, 30, 20))  # asymmetric, opaque
    in_tex = ctx.texture((w, h), 4)
    in_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    in_tex.write(surf.get_buffer())

    def run(clears):
        # Match the game's blend state during the shader chain.
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        pool = FBOPool(ctx)
        # Pre-dirty a pooled FBO, then release it so the pass reuses it.
        fbo, tex = pool.acquire(w, h)
        fbo.use()
        fbo.clear(0.9, 0.1, 0.7, 1.0)
        pool.release(fbo, tex)
        sp = ShaderPass(ctx, NORMALIZE_FRAG)
        sp.clears = clears
        _, out = sp.apply(in_tex, pool, sp._vao, w, h)
        return ctx.framebuffer(color_attachments=[out]).read(components=4)

    cleared = run(True)
    skipped = run(False)
    diff = sum(1 for k in range(0, len(cleared), 4)
               if cleared[k:k + 3] != skipped[k:k + 3])
    print("== Clear-removal: opaque pass, clears=True vs False (blend on) ==")
    print("  RGB pixels differing: %d of %d" % (diff, w * h))
    ok = diff == 0
    print("  RESULT: %s" % ("PASS (clear is redundant)" if ok else "FAIL"))
    print()
    return ok


def verify_squared_distance():
    """Assert squared distance is order-equivalent to hypot for the
    comparisons/argmins used in the space-shooter hot loops (v13.0.0)."""
    import math

    # Deterministic pseudo-random points (no Math.random in this env anyway).
    pts = [((i * 37 % 211) - 105, (i * 53 % 197) - 98) for i in range(400)]
    origin = (7, -11)

    def hypot_key(p):
        return math.hypot(p[0] - origin[0], p[1] - origin[1])

    def sq_key(p):
        return (p[0] - origin[0]) ** 2 + (p[1] - origin[1]) ** 2

    # argmin equivalence
    argmin_ok = min(pts, key=hypot_key) == min(pts, key=sq_key)
    # sort-order equivalence
    sort_ok = [hypot_key(p) for p in sorted(pts, key=hypot_key)] == \
              [hypot_key(p) for p in sorted(pts, key=sq_key)]
    # threshold equivalence (the `< 200` count case)
    thr = 200
    thr_ok = all((hypot_key(p) < thr) == (sq_key(p) < thr * thr) for p in pts)

    ok = argmin_ok and sort_ok and thr_ok
    print("== Squared-distance equivalence (space-shooter hot loops) ==")
    print("  argmin match: %s | sort-order match: %s | threshold match: %s"
          % (argmin_ok, sort_ok, thr_ok))
    print("  RESULT: %s" % ("PASS" if ok else "FAIL"))
    print()
    return ok


if __name__ == "__main__":
    benchmark_upload()
    results = [
        verify_correctness(),
        verify_clear_removal(),
        verify_squared_distance(),
    ]
    sys.exit(0 if all(results) else 1)
