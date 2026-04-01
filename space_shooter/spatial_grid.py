"""Spatial grid for efficient collision detection and neighbor queries."""

from collections import defaultdict


class SpatialGrid:
    """Uniform grid spatial partitioning for O(1) neighbor lookups.

    Divides 2D space into fixed-size cells. Entities are inserted into
    all cells they overlap, and queries return entities in nearby cells.
    Dramatically reduces collision checks from O(n*m) to near-O(n).
    """

    def __init__(self, cell_size=200):
        self.cell_size = cell_size
        self._inv_cell = 1.0 / cell_size
        self._cells = defaultdict(list)

    def clear(self):
        """Reset all cells for the next frame."""
        self._cells.clear()

    def insert(self, entity, x, y, half_extent=0):
        """Insert entity into all overlapping cells.

        Args:
            entity: Any object to store.
            x, y: Center position.
            half_extent: Half the bounding box size (entities spanning
                         multiple cells are inserted into each).
        """
        inv = self._inv_cell
        min_cx = int((x - half_extent) * inv)
        max_cx = int((x + half_extent) * inv)
        min_cy = int((y - half_extent) * inv)
        max_cy = int((y + half_extent) * inv)
        cells = self._cells
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                cells[(cx, cy)].append(entity)

    def query(self, x, y, half_extent=0):
        """Return all entities in cells overlapping the query region.

        Args:
            x, y: Center of query region.
            half_extent: Half the bounding box of the query area.

        Returns:
            List of entities (may contain duplicates if entity spans cells).
        """
        inv = self._inv_cell
        min_cx = int((x - half_extent) * inv)
        max_cx = int((x + half_extent) * inv)
        min_cy = int((y - half_extent) * inv)
        max_cy = int((y + half_extent) * inv)
        cells = self._cells
        result = []
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                bucket = cells.get((cx, cy))
                if bucket:
                    result.extend(bucket)
        return result

    def query_unique(self, x, y, half_extent=0):
        """Like query() but deduplicates results using object identity."""
        seen = set()
        result = []
        for entity in self.query(x, y, half_extent):
            eid = id(entity)
            if eid not in seen:
                seen.add(eid)
                result.append(entity)
        return result
