"""
GPU Shader Effects Package for Stargwent

Each module provides a ShaderPass subclass (or factory function)
that plugs into the GPURenderer effect chain.
"""

from gpu_renderer import MODERNGL_AVAILABLE


def register_all_effects(gpu_renderer):
    """Register all shader effects with the GPU renderer."""
    if not MODERNGL_AVAILABLE or not gpu_renderer or not gpu_renderer.enabled:
        return

    ctx = gpu_renderer.ctx

    try:
        from shaders.bloom import create_bloom_passes
        bloom_passes = create_bloom_passes(ctx)
        gpu_renderer.add_effect("bloom", bloom_passes)
        print("[GPU] Bloom effect registered")
    except Exception as e:
        print(f"[GPU] Failed to register bloom: {e}")

    try:
        from shaders.vignette import create_vignette_pass
        vignette_pass = create_vignette_pass(ctx)
        gpu_renderer.add_effect("vignette", vignette_pass)
        print("[GPU] Vignette effect registered")
    except Exception as e:
        print(f"[GPU] Failed to register vignette: {e}")

    try:
        from shaders.crt_hologram import create_crt_pass
        crt_pass = create_crt_pass(ctx)
        gpu_renderer.add_effect("crt_hologram", crt_pass)
        gpu_renderer.set_effect_enabled("crt_hologram", True)  # MALP feed scanlines
        print("[GPU] CRT/Hologram effect registered")
    except Exception as e:
        print(f"[GPU] Failed to register CRT: {e}")

    try:
        from shaders.distortion import create_distortion_pass
        distortion_pass = create_distortion_pass(ctx)
        gpu_renderer.add_effect("distortion", distortion_pass)
        print("[GPU] Distortion effect registered")
    except Exception as e:
        print(f"[GPU] Failed to register distortion: {e}")

    try:
        from shaders.event_horizon import create_event_horizon_pass
        eh_pass = create_event_horizon_pass(ctx)
        gpu_renderer.add_effect("event_horizon", eh_pass)
        gpu_renderer.set_effect_enabled("event_horizon", False)  # Driven by animation
        print("[GPU] Event horizon effect registered")
    except Exception as e:
        print(f"[GPU] Failed to register event horizon: {e}")

    try:
        from shaders.kawoosh import create_kawoosh_pass
        kawoosh_pass = create_kawoosh_pass(ctx)
        gpu_renderer.add_effect("kawoosh", kawoosh_pass)
        gpu_renderer.set_effect_enabled("kawoosh", False)  # Driven by animation
        print("[GPU] Kawoosh effect registered")
    except Exception as e:
        print(f"[GPU] Failed to register kawoosh: {e}")

    try:
        from shaders.hyperspace import create_hyperspace_pass
        hs_pass = create_hyperspace_pass(ctx)
        gpu_renderer.add_effect("hyperspace", hs_pass)
        gpu_renderer.set_effect_enabled("hyperspace", False)  # Driven by transition
        print("[GPU] Hyperspace effect registered")
    except Exception as e:
        print(f"[GPU] Failed to register hyperspace: {e}")

    try:
        from shaders.asgard_beam import create_asgard_beam_pass
        beam_pass = create_asgard_beam_pass(ctx)
        gpu_renderer.add_effect("asgard_beam", beam_pass)
        gpu_renderer.set_effect_enabled("asgard_beam", False)  # Driven by animation
        print("[GPU] Asgard beam effect registered")
    except Exception as e:
        print(f"[GPU] Failed to register asgard beam: {e}")

    try:
        from shaders.zpm_surge import create_zpm_surge_pass
        zpm_pass = create_zpm_surge_pass(ctx)
        gpu_renderer.add_effect("zpm_surge", zpm_pass)
        gpu_renderer.set_effect_enabled("zpm_surge", False)  # Driven by animation
        print("[GPU] ZPM surge effect registered")
    except Exception as e:
        print(f"[GPU] Failed to register ZPM surge: {e}")

    try:
        from shaders.shockwave import create_shockwave_pass
        sw_pass = create_shockwave_pass(ctx)
        gpu_renderer.add_effect("shockwave", sw_pass)
        gpu_renderer.set_effect_enabled("shockwave", False)  # Driven by transition
        print("[GPU] Shockwave effect registered")
    except Exception as e:
        print(f"[GPU] Failed to register shockwave: {e}")
