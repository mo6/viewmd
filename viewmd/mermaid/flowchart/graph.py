"""Flowchart render-domain model, layout, and drawing composition. Ported from
cmd/graph.go, cmd/mapping_node.go, cmd/mapping_edge.go, and the flowchart-facing
parts of cmd/arrow.go/cmd/draw.go (`drawEdge`/`drawNode`/`drawArrow` and
friends) -- kept together in one module because upstream itself keeps them as
methods on a single `*graph` receiver; splitting node/edge/subgraph handling
into separate "generic" modules would be a fictitious boundary the reference
implementation doesn't actually have."""

from __future__ import annotations

from dataclasses import dataclass, field

from viewmd.mermaid.flowchart.parser import (
    GraphNodeSpec,
    GraphProperties,
    StyleClass,
    TextEdge,
    TextSubgraph,
)
from viewmd.mermaid.grid import astar, canvas
from viewmd.mermaid.grid.canvas import Drawing
from viewmd.mermaid.grid.coords import (
    DOWN,
    LEFT,
    LOWER_LEFT,
    LOWER_RIGHT,
    MIDDLE,
    RIGHT,
    UP,
    UPPER_LEFT,
    UPPER_RIGHT,
    Direction,
    DrawingCoord,
    GridCoord,
    determine_direction,
    determine_start_and_end_dir,
    opposite,
    self_reference_direction,
)
from viewmd.mermaid.grid.label import GraphLabel

_EMPTY_STYLE_CLASS = StyleClass(name="", styles={})


@dataclass
class Node:
    name: str
    label: GraphLabel
    index: int
    style_class_name: str = ""
    style_class: StyleClass = field(default_factory=lambda: _EMPTY_STYLE_CLASS)
    grid_coord: GridCoord | None = None
    drawing_coord: DrawingCoord | None = None
    drawing: Drawing | None = None
    drawn: bool = False


@dataclass
class Edge:
    from_: Node
    to: Node
    text: str = ""
    is_bidirectional: bool = False
    path: list[GridCoord] = field(default_factory=list)
    label_line: list[GridCoord] = field(default_factory=list)
    start_dir: Direction = MIDDLE
    end_dir: Direction = MIDDLE


@dataclass
class Subgraph:
    name: str
    label: GraphLabel
    nodes: list[Node] = field(default_factory=list)
    parent: Subgraph | None = None
    children: list[Subgraph] = field(default_factory=list)
    min_x: int = 0
    min_y: int = 0
    max_x: int = 0
    max_y: int = 0


class Graph:
    def __init__(self) -> None:
        self.nodes: list[Node] = []
        self.edges: list[Edge] = []
        self.drawing: Drawing = canvas.mk_drawing(0, 0)
        self.grid: dict[GridCoord, Node] = {}
        self.edge_counts: dict[tuple[int, int], int] = {}
        self.column_width: dict[int, int] = {}
        self.row_height: dict[int, int] = {}
        self.style_classes: dict[str, StyleClass] = {}
        self.box_border_padding: int = 1
        self.graph_direction: str = "TD"
        self.padding_x: int = 5
        self.padding_y: int = 5
        self.subgraphs: list[Subgraph] = []
        self.offset_x: int = 0
        self.offset_y: int = 0
        self.use_ascii: bool = False

    # -- construction -----------------------------------------------------

    def get_node(self, name: str) -> Node | None:
        for n in self.nodes:
            if n.name == name:
                return n
        return None

    def append_node(self, n: Node) -> None:
        self.nodes.append(n)

    def set_style_classes(self, properties: GraphProperties) -> None:
        self.style_classes = properties.style_classes
        self.box_border_padding = properties.box_border_padding
        self.graph_direction = properties.graph_direction
        self.padding_x = properties.padding_x
        self.padding_y = properties.padding_y
        for n in self.nodes:
            if n.style_class_name:
                n.style_class = self.style_classes.get(n.style_class_name, _EMPTY_STYLE_CLASS)

    def set_subgraphs(self, text_subgraphs: list[TextSubgraph]) -> None:
        self.subgraphs = []
        for tsg in text_subgraphs:
            sg = Subgraph(name=tsg.name, label=tsg.label, nodes=[], children=[])
            for node_name in tsg.nodes:
                node = self.get_node(node_name)
                if node is not None:
                    sg.nodes.append(node)
            self.subgraphs.append(sg)

        for i, tsg in enumerate(text_subgraphs):
            sg = self.subgraphs[i]
            if tsg.parent is not None:
                for j, parent_tsg in enumerate(text_subgraphs):
                    if parent_tsg is tsg.parent:
                        sg.parent = self.subgraphs[j]
                        break
            for child_tsg in tsg.children:
                for j, check_tsg in enumerate(text_subgraphs):
                    if check_tsg is child_tsg:
                        sg.children.append(self.subgraphs[j])
                        break

    def get_edges_from_node(self, n: Node) -> list[Edge]:
        return [e for e in self.edges if e.from_.name == n.name]

    def get_children(self, n: Node) -> list[Node]:
        return [e.to for e in self.get_edges_from_node(n) if e.from_.name == n.name]

    # -- layout -------------------------------------------------------------

    def create_mapping(self) -> None:
        highest_position_per_level: dict[int, int] = {}

        nodes_found: set[str] = set()
        root_nodes: list[Node] = []
        for n in self.nodes:
            if n.name not in nodes_found:
                root_nodes.append(n)
            nodes_found.add(n.name)
            for child in self.get_children(n):
                nodes_found.add(child.name)

        has_external_roots = False
        has_subgraph_roots_with_edges = False
        for n in root_nodes:
            if self._is_node_in_any_subgraph(n):
                if self.get_children(n):
                    has_subgraph_roots_with_edges = True
            else:
                has_external_roots = True

        should_separate = (
            self.graph_direction == "LR" and has_external_roots and has_subgraph_roots_with_edges
        )

        if should_separate:
            external_root_nodes = [n for n in root_nodes if not self._is_node_in_any_subgraph(n)]
            subgraph_root_nodes = [n for n in root_nodes if self._is_node_in_any_subgraph(n)]
        else:
            external_root_nodes = root_nodes
            subgraph_root_nodes = []

        for n in external_root_nodes:
            pos = highest_position_per_level.get(0, 0)
            coord = GridCoord(0, pos) if self.graph_direction == "LR" else GridCoord(pos, 0)
            mapping_coord = self._reserve_spot_in_grid(self.nodes[n.index], coord)
            self.nodes[n.index].grid_coord = mapping_coord
            highest_position_per_level[0] = pos + 4

        if should_separate and subgraph_root_nodes:
            subgraph_level = 4
            for n in subgraph_root_nodes:
                pos = highest_position_per_level.get(subgraph_level, 0)
                coord = (
                    GridCoord(subgraph_level, pos)
                    if self.graph_direction == "LR"
                    else GridCoord(pos, subgraph_level)
                )
                mapping_coord = self._reserve_spot_in_grid(self.nodes[n.index], coord)
                self.nodes[n.index].grid_coord = mapping_coord
                highest_position_per_level[subgraph_level] = pos + 4

        for n in self.nodes:
            child_level = n.grid_coord.x + 4 if self.graph_direction == "LR" else n.grid_coord.y + 4
            highest_position = highest_position_per_level.get(child_level, 0)
            for child in self.get_children(n):
                if child.grid_coord is not None:
                    continue
                coord = (
                    GridCoord(child_level, highest_position)
                    if self.graph_direction == "LR"
                    else GridCoord(highest_position, child_level)
                )
                mapping_coord = self._reserve_spot_in_grid(self.nodes[child.index], coord)
                self.nodes[child.index].grid_coord = mapping_coord
                highest_position_per_level[child_level] = highest_position + 4

        for n in self.nodes:
            self._set_column_width(n)

        for e in self.edges:
            self._determine_path(e)
            self._increase_grid_size_for_path(e.path)
            self._determine_label_line(e)

        for n in self.nodes:
            dc = self._grid_to_drawing_coord(n.grid_coord)
            n.drawing_coord = dc
            n.drawing = canvas.draw_box(
                self._node_box_width(n),
                self._node_box_height(n),
                n.label,
                n.style_class.styles.get("color", ""),
                self.use_ascii,
            )
        self._set_drawing_size_to_grid_constraints()

        self._calculate_subgraph_bounding_boxes()
        self._offset_drawing_for_subgraphs()

    def _is_node_in_any_subgraph(self, n: Node) -> bool:
        return any(sg_node is n for sg in self.subgraphs for sg_node in sg.nodes)

    def _get_node_subgraph(self, n: Node) -> Subgraph | None:
        for sg in self.subgraphs:
            if any(sg_node is n for sg_node in sg.nodes):
                return sg
        return None

    def _has_incoming_edge_from_outside_subgraph(self, n: Node) -> bool:
        node_subgraph = self._get_node_subgraph(n)
        if node_subgraph is None:
            return False

        has_external_edge = False
        for e in self.edges:
            if e.to is n:
                source_subgraph = self._get_node_subgraph(e.from_)
                if source_subgraph is not node_subgraph:
                    has_external_edge = True
                    break
        if not has_external_edge:
            return False

        for other in node_subgraph.nodes:
            if other is n or other.grid_coord is None:
                continue
            other_has_external = False
            for e in self.edges:
                if e.to is other:
                    source_subgraph = self._get_node_subgraph(e.from_)
                    if source_subgraph is not node_subgraph:
                        other_has_external = True
                        break
            if other_has_external and other.grid_coord.y < n.grid_coord.y:
                return False

        return True

    def _set_column_width(self, n: Node) -> None:
        col1, col2, col3 = 1, 2 * self.box_border_padding + n.label.width, 1
        for idx, col in enumerate((col1, col2, col3)):
            x_coord = n.grid_coord.x + idx
            self.column_width[x_coord] = max(self.column_width.get(x_coord, 0), col)

        for idx, row in enumerate((1, n.label.content_height() + 2 * self.box_border_padding, 1)):
            y_coord = n.grid_coord.y + idx
            self.row_height[y_coord] = max(self.row_height.get(y_coord, 0), row)

        if n.grid_coord.x > 0:
            self.column_width[n.grid_coord.x - 1] = self.padding_x
        if n.grid_coord.y > 0:
            base_padding = self.padding_y
            if self._has_incoming_edge_from_outside_subgraph(n):
                base_padding += 4  # subgraph border/label overhead
            self.row_height[n.grid_coord.y - 1] = max(
                self.row_height.get(n.grid_coord.y - 1, 0), base_padding
            )

    def _increase_grid_size_for_path(self, path: list[GridCoord]) -> None:
        for c in path:
            self.column_width.setdefault(c.x, self.padding_x // 2)
            self.row_height.setdefault(c.y, self.padding_y // 2)

    def _reserve_spot_in_grid(self, n: Node, requested_coord: GridCoord) -> GridCoord:
        if self.grid.get(requested_coord) is not None:
            if self.graph_direction == "LR":
                return self._reserve_spot_in_grid(
                    n, GridCoord(requested_coord.x, requested_coord.y + 4)
                )
            return self._reserve_spot_in_grid(
                n, GridCoord(requested_coord.x + 4, requested_coord.y)
            )

        for dx in range(3):
            for dy in range(3):
                self.grid[GridCoord(requested_coord.x + dx, requested_coord.y + dy)] = n
        n.grid_coord = requested_coord
        return requested_coord

    # -- edge routing ---------------------------------------------------------

    def _is_free_in_grid(self, c: GridCoord) -> bool:
        if c.x < 0 or c.y < 0:
            return False
        return self.grid.get(c) is None

    def _get_path(self, from_: GridCoord, to: GridCoord) -> list[GridCoord] | None:
        return astar.find_path(from_, to, self._is_free_in_grid)

    def _edge_pair(self, a: int, b: int) -> tuple[int, int]:
        return (a, b) if a < b else (b, a)

    def _parallel_directions(
        self, e: Edge, duplicate_index: int
    ) -> tuple[Direction, Direction, bool]:
        if duplicate_index == 0:
            return MIDDLE, MIDDLE, False
        d = determine_direction(e.from_.grid_coord, e.to.grid_coord)
        if self.graph_direction == "LR" and d in (RIGHT, LEFT):
            options = [(DOWN, DOWN), (UP, UP)]
            if duplicate_index - 1 < len(options):
                return (*options[duplicate_index - 1], True)
        elif self.graph_direction == "TD" and d in (DOWN, UP):
            options = [(RIGHT, RIGHT), (LEFT, LEFT)]
            if duplicate_index - 1 < len(options):
                return (*options[duplicate_index - 1], True)
        return MIDDLE, MIDDLE, False

    def _determine_path(self, e: Edge) -> None:
        key = self._edge_pair(e.from_.index, e.to.index)
        duplicate_index = self.edge_counts.get(key, 0)

        start_dir, end_dir, ok = self._parallel_directions(e, duplicate_index)
        if ok:
            from_ = GridCoord(
                e.from_.grid_coord.x + start_dir.x, e.from_.grid_coord.y + start_dir.y
            )
            to = GridCoord(e.to.grid_coord.x + end_dir.x, e.to.grid_coord.y + end_dir.y)
            path = self._get_path(from_, to)
            if path is not None:
                e.start_dir = start_dir
                e.end_dir = end_dir
                e.path = astar.merge_path(path)
                self.edge_counts[key] = duplicate_index + 1
                return

        if e.from_ is e.to:
            preferred_dir, preferred_opposite_dir, alternative_dir, alternative_opposite_dir = (
                self_reference_direction(self.graph_direction)
            )
        else:
            preferred_dir, preferred_opposite_dir, alternative_dir, alternative_opposite_dir = (
                determine_start_and_end_dir(
                    self.graph_direction, e.from_.grid_coord, e.to.grid_coord
                )
            )

        from_ = GridCoord(
            e.from_.grid_coord.x + preferred_dir.x, e.from_.grid_coord.y + preferred_dir.y
        )
        to = GridCoord(
            e.to.grid_coord.x + preferred_opposite_dir.x,
            e.to.grid_coord.y + preferred_opposite_dir.y,
        )
        preferred_path = self._get_path(from_, to)
        if preferred_path is None:
            # Upstream bug (cmd/mapping_edge.go's `determinePath`): the
            # alternative path is never actually computed on this branch, so
            # the edge is left with no path at all -- replicated verbatim.
            e.start_dir = alternative_dir
            e.end_dir = alternative_opposite_dir
            e.path = []
            return
        preferred_path = astar.merge_path(preferred_path)

        from_ = GridCoord(
            e.from_.grid_coord.x + alternative_dir.x, e.from_.grid_coord.y + alternative_dir.y
        )
        to = GridCoord(
            e.to.grid_coord.x + alternative_opposite_dir.x,
            e.to.grid_coord.y + alternative_opposite_dir.y,
        )
        alternative_path_raw = self._get_path(from_, to)
        # Upstream bug: on failure here, Go sets `e.path = preferredPath` but
        # then unconditionally overwrites it via the step-count comparison
        # below using a nil `alternativePath` (len 0) -- so a failed
        # alternative-path search silently drops the edge's path rather than
        # falling back to the preferred one. Replicated verbatim.
        alternative_path = (
            astar.merge_path(alternative_path_raw) if alternative_path_raw is not None else []
        )

        if len(preferred_path) <= len(alternative_path):
            e.start_dir = preferred_dir
            e.end_dir = preferred_opposite_dir
            e.path = preferred_path
        else:
            e.start_dir = alternative_dir
            e.end_dir = alternative_opposite_dir
            e.path = alternative_path
        self.edge_counts[key] = duplicate_index + 1

    def _is_node_column(self, x: int) -> bool:
        for n in self.nodes:
            if n.grid_coord is None:
                continue
            if n.grid_coord.x <= x <= n.grid_coord.x + 2:
                return True
        return False

    def _calculate_line_width(self, line: list[GridCoord]) -> int:
        return sum(self.column_width.get(c.x, 0) for c in line)

    def _determine_label_line(self, e: Edge) -> None:
        len_label = len(e.text)
        if len_label == 0:
            return

        prev_step = e.path[0]
        largest_line: list[GridCoord] | None = None
        largest_line_size = 0
        fallback_line: list[GridCoord] | None = None
        fallback_line_size = 0
        for step in e.path[1:]:
            line = [prev_step, step]
            prev_step = step
            line_width = self._calculate_line_width(line)
            if self._is_node_column(_label_middle_x(line)):
                if line_width > fallback_line_size:
                    fallback_line_size = line_width
                    fallback_line = line
                continue
            if line_width >= len_label:
                largest_line = line
                break
            if line_width > largest_line_size:
                largest_line_size = line_width
                largest_line = line

        if largest_line is None:
            largest_line = fallback_line
        if largest_line is None:
            largest_line = [e.path[0], e.path[1]]

        middle_x = _label_middle_x(largest_line)
        label_padding = 4 if e.is_bidirectional else 3
        self.column_width[middle_x] = max(
            self.column_width.get(middle_x, 0), len_label + label_padding
        )
        e.label_line = largest_line

    def _grid_to_drawing_coord(self, c: GridCoord, dir_: Direction | None = None) -> DrawingCoord:
        target = c if dir_ is None else GridCoord(c.x + dir_.x, c.y + dir_.y)
        x = sum(self.column_width.get(col, 0) for col in range(target.x))
        y = sum(self.row_height.get(row, 0) for row in range(target.y))
        return DrawingCoord(
            x + self.column_width.get(target.x, 0) // 2 + self.offset_x,
            y + self.row_height.get(target.y, 0) // 2 + self.offset_y,
        )

    def _line_to_drawing(self, line: list[GridCoord]) -> list[DrawingCoord]:
        return [self._grid_to_drawing_coord(c) for c in line]

    def _node_box_width(self, n: Node) -> int:
        return self.column_width.get(n.grid_coord.x, 0) + self.column_width.get(
            n.grid_coord.x + 1, 0
        )

    def _node_box_height(self, n: Node) -> int:
        return self.row_height.get(n.grid_coord.y, 0) + self.row_height.get(n.grid_coord.y + 1, 0)

    def _set_drawing_size_to_grid_constraints(self) -> None:
        max_x = sum(self.column_width.values())
        max_y = sum(self.row_height.values())
        self.drawing = canvas.increase_size(self.drawing, max_x - 1, max_y - 1)

    # -- subgraph bounding boxes ------------------------------------------

    def _calculate_subgraph_bounding_boxes(self) -> None:
        for sg in self.subgraphs:
            self._calculate_subgraph_bounding_box(sg)
        self._ensure_subgraph_spacing()

    def _calculate_subgraph_bounding_box(self, sg: Subgraph) -> None:
        if not sg.nodes:
            return

        min_x = min_y = 1_000_000
        max_x = max_y = -1_000_000

        for child in sg.children:
            self._calculate_subgraph_bounding_box(child)
            if child.nodes:
                min_x, min_y = min(min_x, child.min_x), min(min_y, child.min_y)
                max_x, max_y = max(max_x, child.max_x), max(max_y, child.max_y)

        for n in sg.nodes:
            if n.drawing_coord is None or n.drawing is None:
                continue
            node_min_x, node_min_y = n.drawing_coord.x, n.drawing_coord.y
            node_max_x = node_min_x + len(n.drawing) - 1
            node_max_y = node_min_y + len(n.drawing[0]) - 1
            min_x, min_y = min(min_x, node_min_x), min(min_y, node_min_y)
            max_x, max_y = max(max_x, node_max_x), max(max_y, node_max_y)

        current_width = max_x - min_x
        current_inner_width = current_width + 3
        if current_inner_width < sg.label.width:
            extra_width = sg.label.width - current_inner_width
            min_x -= extra_width // 2
            max_x += extra_width - extra_width // 2

        subgraph_padding = 2
        subgraph_label_space = sg.label.content_height() + 1
        sg.min_x = min_x - subgraph_padding
        sg.min_y = min_y - subgraph_padding - subgraph_label_space
        sg.max_x = max_x + subgraph_padding
        sg.max_y = max_y + subgraph_padding

    def _ensure_subgraph_spacing(self) -> None:
        min_spacing = 1
        root_subgraphs = [sg for sg in self.subgraphs if sg.parent is None and sg.nodes]

        for i in range(len(root_subgraphs)):
            for j in range(i + 1, len(root_subgraphs)):
                sg1, sg2 = root_subgraphs[i], root_subgraphs[j]

                if sg1.min_x < sg2.max_x and sg1.max_x > sg2.min_x:
                    if sg1.max_y >= sg2.min_y - min_spacing and sg1.min_y < sg2.min_y:
                        sg2.min_y = sg1.max_y + min_spacing + 1
                    elif sg2.max_y >= sg1.min_y - min_spacing and sg2.min_y < sg1.min_y:
                        sg1.min_y = sg2.max_y + min_spacing + 1

                if sg1.min_y < sg2.max_y and sg1.max_y > sg2.min_y:
                    if sg1.max_x >= sg2.min_x - min_spacing and sg1.min_x < sg2.min_x:
                        sg2.min_x = sg1.max_x + min_spacing + 1
                    elif sg2.max_x >= sg1.min_x - min_spacing and sg2.min_x < sg1.min_x:
                        sg1.min_x = sg2.max_x + min_spacing + 1

    def _offset_drawing_for_subgraphs(self) -> None:
        if not self.subgraphs:
            return

        min_x = min([0] + [sg.min_x for sg in self.subgraphs])
        min_y = min([0] + [sg.min_y for sg in self.subgraphs])
        offset_x, offset_y = -min_x, -min_y
        if offset_x == 0 and offset_y == 0:
            return

        self.offset_x, self.offset_y = offset_x, offset_y

        for sg in self.subgraphs:
            sg.min_x += offset_x
            sg.min_y += offset_y
            sg.max_x += offset_x
            sg.max_y += offset_y

        for n in self.nodes:
            if n.drawing_coord is not None:
                n.drawing_coord = DrawingCoord(
                    n.drawing_coord.x + offset_x, n.drawing_coord.y + offset_y
                )

    # -- drawing --------------------------------------------------------------

    def draw(self) -> Drawing:
        self._draw_subgraphs()

        for node in self.nodes:
            if not node.drawn:
                self._draw_node(node)

        line_drawings, corner_drawings, arrow_head_drawings, box_start_drawings, label_drawings = (
            [],
            [],
            [],
            [],
            [],
        )
        for e in self.edges:
            line, box_start, arrow_head, corners, label = self._draw_edge(e)
            line_drawings.append(line)
            corner_drawings.append(corners)
            arrow_head_drawings.append(arrow_head)
            box_start_drawings.append(box_start)
            label_drawings.append(label)

        origin = DrawingCoord(0, 0)
        self.drawing = canvas.merge_drawings(
            self.drawing, origin, *line_drawings, use_ascii=self.use_ascii
        )
        self.drawing = canvas.merge_drawings(
            self.drawing, origin, *corner_drawings, use_ascii=self.use_ascii
        )
        self.drawing = canvas.merge_drawings(
            self.drawing, origin, *arrow_head_drawings, use_ascii=self.use_ascii
        )
        self.drawing = canvas.merge_drawings(
            self.drawing, origin, *box_start_drawings, use_ascii=self.use_ascii
        )
        self.drawing = canvas.merge_drawings(
            self.drawing, origin, *label_drawings, use_ascii=self.use_ascii
        )

        self._draw_subgraph_labels()
        return self.drawing

    def _draw_node(self, n: Node) -> None:
        self.drawing = canvas.merge_drawings(
            self.drawing, n.drawing_coord, n.drawing, use_ascii=self.use_ascii
        )
        n.drawn = True

    def _draw_subgraphs(self) -> None:
        for sg in self._sorted_subgraphs_by_depth():
            sg_drawing = canvas.draw_subgraph(
                sg.max_x - sg.min_x, sg.max_y - sg.min_y, self.use_ascii
            )
            offset = DrawingCoord(sg.min_x, sg.min_y)
            self.drawing = canvas.merge_drawings(
                self.drawing, offset, sg_drawing, use_ascii=self.use_ascii
            )

    def _draw_subgraph_labels(self) -> None:
        for sg in self.subgraphs:
            if not sg.nodes:
                continue
            label_drawing = canvas.draw_subgraph_label(
                sg.max_x - sg.min_x, sg.max_y - sg.min_y, sg.label
            )
            offset = DrawingCoord(sg.min_x, sg.min_y)
            self.drawing = canvas.merge_drawings(
                self.drawing, offset, label_drawing, use_ascii=self.use_ascii
            )

    def _sorted_subgraphs_by_depth(self) -> list[Subgraph]:
        depths = {id(sg): self._subgraph_depth(sg) for sg in self.subgraphs}
        sorted_sgs = list(self.subgraphs)
        for i in range(len(sorted_sgs)):
            for j in range(i + 1, len(sorted_sgs)):
                if depths[id(sorted_sgs[i])] > depths[id(sorted_sgs[j])]:
                    sorted_sgs[i], sorted_sgs[j] = sorted_sgs[j], sorted_sgs[i]
        return sorted_sgs

    def _subgraph_depth(self, sg: Subgraph) -> int:
        depth = 0
        while sg.parent is not None:
            depth += 1
            sg = sg.parent
        return depth

    def _draw_edge(self, e: Edge) -> tuple[Drawing, Drawing, Drawing, Drawing, Drawing]:
        from_ = GridCoord(
            e.from_.grid_coord.x + e.start_dir.x, e.from_.grid_coord.y + e.start_dir.y
        )
        to = GridCoord(e.to.grid_coord.x + e.end_dir.x, e.to.grid_coord.y + e.end_dir.y)
        return self._draw_arrow(from_, to, e)

    def _draw_arrow(
        self, from_: GridCoord, to: GridCoord, e: Edge
    ) -> tuple[Drawing, Drawing, Drawing, Drawing, Drawing]:
        blank = canvas.copy_canvas(self.drawing)
        if not e.path:
            return blank, blank, blank, blank, blank

        d_label = self._draw_arrow_label(e)
        d_path, lines_drawn, line_dirs = self._draw_path(e.path)
        d_box_start = self._draw_box_start(e.path, lines_drawn[0])
        d_arrow_head = self._draw_arrow_head(lines_drawn[-1], line_dirs[-1])
        if e.is_bidirectional and lines_drawn:
            d_start_arrow_head = self._draw_arrow_head(
                list(reversed(lines_drawn[0])), opposite(line_dirs[0])
            )
            d_arrow_head = canvas.merge_drawings(
                d_arrow_head, DrawingCoord(0, 0), d_start_arrow_head, use_ascii=self.use_ascii
            )
        d_corners = self._draw_corners(e.path)
        return d_path, d_box_start, d_arrow_head, d_corners, d_label

    def _draw_path(
        self, path: list[GridCoord]
    ) -> tuple[Drawing, list[list[DrawingCoord]], list[Direction]]:
        d = canvas.copy_canvas(self.drawing)
        previous_coord = path[0]
        lines_drawn: list[list[DrawingCoord]] = []
        line_dirs: list[Direction] = []
        for next_coord in path[1:]:
            previous_drawing_coord = self._grid_to_drawing_coord(previous_coord)
            next_drawing_coord = self._grid_to_drawing_coord(next_coord)
            if previous_drawing_coord == next_drawing_coord:
                continue
            dir_ = determine_direction(previous_coord, next_coord)
            s = canvas.draw_line(
                d, previous_drawing_coord, next_drawing_coord, 1, -1, self.use_ascii
            )
            if not s:
                s = [previous_drawing_coord]
            lines_drawn.append(s)
            line_dirs.append(dir_)
            previous_coord = next_coord
        return d, lines_drawn, line_dirs

    def _draw_box_start(self, path: list[GridCoord], first_line: list[DrawingCoord]) -> Drawing:
        d = canvas.copy_canvas(self.drawing)
        if self.use_ascii:
            return d
        from_ = first_line[0]
        dir_ = determine_direction(path[0], path[1])
        if dir_ == UP:
            d[from_.x][from_.y + 1] = "┴"
        elif dir_ == DOWN:
            d[from_.x][from_.y - 1] = "┬"
        elif dir_ == LEFT:
            d[from_.x + 1][from_.y] = "┤"
        elif dir_ == RIGHT:
            d[from_.x - 1][from_.y] = "├"
        return d

    _UNICODE_ARROWHEADS = {
        UP: "▲",
        DOWN: "▼",
        LEFT: "◄",
        RIGHT: "►",
        UPPER_RIGHT: "◥",
        UPPER_LEFT: "◤",
        LOWER_RIGHT: "◢",
        LOWER_LEFT: "◣",
    }
    _ASCII_ARROWHEADS = {UP: "^", DOWN: "v", LEFT: "<", RIGHT: ">"}

    def _draw_arrow_head(self, line: list[DrawingCoord], fallback: Direction) -> Drawing:
        d = canvas.copy_canvas(self.drawing)
        if not line:
            return d
        from_ = line[0]
        last_pos = line[-1]
        dir_ = determine_direction(from_, last_pos)
        if len(line) == 1 or dir_ == MIDDLE:
            dir_ = fallback

        if not self.use_ascii:
            char = self._UNICODE_ARROWHEADS.get(dir_) or self._UNICODE_ARROWHEADS.get(fallback, "●")
        else:
            char = self._ASCII_ARROWHEADS.get(dir_) or self._ASCII_ARROWHEADS.get(fallback, "*")

        d[last_pos.x][last_pos.y] = char
        return d

    def _draw_corners(self, path: list[GridCoord]) -> Drawing:
        d = canvas.copy_canvas(self.drawing)
        for idx in range(1, len(path) - 1):
            coord = path[idx]
            drawing_coord = self._grid_to_drawing_coord(coord)
            prev_dir = determine_direction(path[idx - 1], coord)
            next_dir = determine_direction(coord, path[idx + 1])

            if self.use_ascii:
                corner = "+"
            elif (prev_dir == RIGHT and next_dir == DOWN) or (prev_dir == UP and next_dir == LEFT):
                corner = "┐"
            elif (prev_dir == RIGHT and next_dir == UP) or (prev_dir == DOWN and next_dir == LEFT):
                corner = "┘"
            elif (prev_dir == LEFT and next_dir == DOWN) or (prev_dir == UP and next_dir == RIGHT):
                corner = "┌"
            elif (prev_dir == LEFT and next_dir == UP) or (prev_dir == DOWN and next_dir == RIGHT):
                corner = "└"
            else:
                corner = "+"

            d[drawing_coord.x][drawing_coord.y] = corner
        return d

    def _draw_arrow_label(self, e: Edge) -> Drawing:
        d = canvas.copy_canvas(self.drawing)
        if len(e.text) == 0:
            return d
        line = self._line_to_drawing(e.label_line)
        line = _inset_line(line, 2, 2) if e.is_bidirectional else _inset_line(line, 1, 2)
        return canvas.draw_text_on_line(d, line, e.text)


def _label_middle_x(line: list[GridCoord]) -> int:
    min_x, max_x = sorted((line[0].x, line[1].x))
    return min_x + (max_x - min_x) // 2


def _inset_line(line: list[DrawingCoord], inset_start: int, inset_end: int) -> list[DrawingCoord]:
    if len(line) < 2 or (inset_start == 0 and inset_end == 0):
        return line
    end_inset = inset_end - 1 if inset_end > 0 else inset_end
    dir_ = determine_direction(line[0], line[1])
    a, b = line[0], line[1]
    if dir_ == RIGHT:
        a, b = DrawingCoord(a.x + inset_start, a.y), DrawingCoord(b.x - end_inset, b.y)
    elif dir_ == LEFT:
        a, b = DrawingCoord(a.x - inset_start, a.y), DrawingCoord(b.x + end_inset, b.y)
    elif dir_ == DOWN:
        a, b = DrawingCoord(a.x, a.y + inset_start), DrawingCoord(b.x, b.y - end_inset)
    elif dir_ == UP:
        a, b = DrawingCoord(a.x, a.y - inset_start), DrawingCoord(b.x, b.y + end_inset)
    else:
        return line
    return [a, b]


def mk_graph(data: dict[str, list[TextEdge]], node_specs: dict[str, GraphNodeSpec]) -> Graph:
    g = Graph()
    index = 0
    for node_name, children in data.items():
        spec = node_specs.get(node_name, GraphNodeSpec())
        parent_node = g.get_node(node_name)
        if parent_node is None:
            parent_node = Node(
                name=node_name, label=spec.label, index=index, style_class_name=spec.style_class
            )
            g.append_node(parent_node)
            index += 1
        for text_edge in children:
            child_spec = node_specs.get(text_edge.child.name, GraphNodeSpec())
            child_node = g.get_node(text_edge.child.name)
            if child_node is None:
                child_node = Node(
                    name=text_edge.child.name,
                    label=child_spec.label,
                    index=index,
                    style_class_name=child_spec.style_class,
                )
                g.append_node(child_node)
                index += 1
            g.edges.append(
                Edge(
                    from_=parent_node,
                    to=child_node,
                    text=text_edge.label,
                    is_bidirectional=text_edge.is_bidirectional,
                )
            )
    return g


def build(properties: GraphProperties) -> Graph:
    g = mk_graph(properties.data, properties.node_specs)
    g.set_style_classes(properties)
    g.use_ascii = properties.use_ascii
    g.set_subgraphs(properties.subgraphs)
    g.create_mapping()
    return g
