/**
 * A table to compare many records on the same fields (plan section 7.4, guidelines 5.4): a sticky
 * header, every meaningful column sortable, and the rows per page chosen by the reader.
 *
 * The table is sized by its content inside a scroll container, never stretched to the window, so
 * a wide screen does not open a hole in the middle of each row. A column that always truncates
 * (an id) gets a fixed `width`. Numbers are right-aligned with tabular figures.
 *
 * With `selected` and `onSelectedChange` each row starts with a checkbox, and the header's selects
 * every row (Phase 10: **Make a playlist** from songs).
 *
 * **Server mode** (Phase 13: the Public Library's 9,000 songs): with `onSortChange` the sort is the
 * caller's and the rows come sorted; with `paging` they come one page at a time, and the page
 * controls say the whole count. The caller asks the backend again on each change.
 */

import { useMemo, useState, type ReactNode } from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";

export interface DataColumn<Row> {
  key: string;
  label: string;
  render: (row: Row) => ReactNode;
  /** The value the column sorts by; a column without one does not sort. */
  sortValue?: (row: Row) => string | number | null;
  align?: "left" | "right";
  /** A fixed width in pixels, for a column that always truncates. */
  width?: number;
  /** The direction of the first click on the header: `desc` for a popularity, `asc` by default. */
  firstDirection?: "asc" | "desc";
}

export type TableSort = { key: string; direction: "asc" | "desc" };

/** One page of rows the server sorted and cut (server mode). */
export interface TablePaging {
  count: number;
  page: number;
  perPage: number;
  onPage: (page: number) => void;
  onPerPage: (perPage: number) => void;
}

export interface DataTableProps<Row> {
  columns: readonly DataColumn<Row>[];
  rows: readonly Row[];
  rowKey: (row: Row) => string;
  onRowClick?: (row: Row) => void;
  initialSort?: { key: string; direction: "asc" | "desc" };
  rowsPerPageOptions?: number[];
  /** The height of the scroll container; the header stays visible inside it. */
  maxHeight?: number | string;
  /** The keys of the rows picked with their checkbox; no checkboxes without it. */
  selected?: ReadonlySet<string>;
  onSelectedChange?: (keys: Set<string>) => void;
  /** Server mode: the sort on show, and what a click on a header asks for. */
  sort?: TableSort | null;
  onSortChange?: (sort: TableSort) => void;
  /** Server mode: the rows are one page of `paging.count`. */
  paging?: TablePaging;
}

export function DataTable<Row>({
  columns,
  rows,
  rowKey,
  onRowClick,
  initialSort,
  rowsPerPageOptions = [25, 50, 100],
  maxHeight = "70vh",
  selected,
  onSelectedChange,
  sort: givenSort,
  onSortChange,
  paging,
}: DataTableProps<Row>) {
  const picking = selected !== undefined && onSelectedChange !== undefined;
  const allKeys = rows.map(rowKey);
  const picked = allKeys.filter((key) => selected?.has(key)).length;
  const toggle = (key: string) => {
    if (!picking) return;
    const next = new Set(selected);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    onSelectedChange(next);
  };
  const [ownSort, setOwnSort] = useState<TableSort | null>(initialSort ?? null);
  const [ownPage, setOwnPage] = useState(0);
  const [ownPerPage, setOwnPerPage] = useState(rowsPerPageOptions[0]);
  const remoteSort = onSortChange !== undefined;
  const sort = remoteSort ? (givenSort ?? null) : ownSort;
  const page = paging ? paging.page : ownPage;
  const perPage = paging ? paging.perPage : ownPerPage;
  const setPage = (next: number) => (paging ? paging.onPage(next) : setOwnPage(next));
  const setPerPage = (next: number) => (paging ? paging.onPerPage(next) : setOwnPerPage(next));
  const total = paging ? paging.count : rows.length;
  const clickSort = (column: DataColumn<Row>) => {
    const next: TableSort =
      sort?.key === column.key
        ? { key: column.key, direction: sort.direction === "asc" ? "desc" : "asc" }
        : { key: column.key, direction: column.firstDirection ?? "asc" };
    if (remoteSort) onSortChange(next);
    else setOwnSort(next);
  };

  const sorted = useMemo(() => {
    const column = sort ? columns.find((one) => one.key === sort.key) : undefined;
    if (remoteSort || !sort || !column?.sortValue) return rows;
    const value = column.sortValue;
    const sign = sort.direction === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const x = value(a);
      const y = value(b);
      if (x === y) return 0;
      // Absent values go last whichever way the column sorts (a dash, never a zero).
      if (x === null) return 1;
      if (y === null) return -1;
      return (x < y ? -1 : 1) * sign;
    });
  }, [rows, columns, sort, remoteSort]);

  const visible = paging ? sorted : sorted.slice(page * perPage, page * perPage + perPage);

  // The page controls stay under the table, at its width, not at the far edge of the page.
  return (
    <Box sx={{ width: "fit-content", maxWidth: "100%" }}>
      <TableContainer sx={{ maxHeight, maxWidth: "100%" }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              {picking ? (
                <TableCell padding="checkbox">
                  <Checkbox
                    size="small"
                    checked={picked > 0 && picked === allKeys.length}
                    indeterminate={picked > 0 && picked < allKeys.length}
                    onChange={() => onSelectedChange(picked === allKeys.length ? new Set() : new Set(allKeys))}
                    slotProps={{ input: { "aria-label": "Select every row" } }}
                  />
                </TableCell>
              ) : null}
              {columns.map((column) => (
                <TableCell
                  key={column.key}
                  align={column.align}
                  sx={{ width: column.width, color: "text.secondary", fontWeight: 500, whiteSpace: "nowrap" }}
                  sortDirection={sort?.key === column.key ? sort.direction : false}
                >
                  {column.sortValue ? (
                    <TableSortLabel
                      active={sort?.key === column.key}
                      direction={sort?.key === column.key ? sort.direction : (column.firstDirection ?? "asc")}
                      onClick={() => clickSort(column)}
                    >
                      {column.label}
                    </TableSortLabel>
                  ) : (
                    column.label
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {visible.map((row) => (
              <TableRow
                key={rowKey(row)}
                hover
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                sx={onRowClick ? { cursor: "pointer" } : undefined}
                selected={picking && selected.has(rowKey(row))}
              >
                {picking ? (
                  <TableCell padding="checkbox" onClick={(event) => event.stopPropagation()}>
                    <Checkbox
                      size="small"
                      checked={selected.has(rowKey(row))}
                      onChange={() => toggle(rowKey(row))}
                      slotProps={{ input: { "aria-label": "Select this row" } }}
                    />
                  </TableCell>
                ) : null}
                {columns.map((column) => (
                  <TableCell
                    key={column.key}
                    align={column.align}
                    sx={{
                      width: column.width,
                      maxWidth: column.width,
                      ...(column.align === "right" ? { fontVariantNumeric: "tabular-nums" } : {}),
                    }}
                  >
                    {column.render(row)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {total > rowsPerPageOptions[0] ? (
        <TablePagination
          component="div"
          count={total}
          page={page}
          onPageChange={(_event, next) => setPage(next)}
          rowsPerPage={perPage}
          rowsPerPageOptions={rowsPerPageOptions}
          // Narrow, only the range and the arrows: the rows-per-page choice would push them off the page.
          sx={{ "& .MuiTablePagination-selectLabel, & .MuiTablePagination-input": { display: { xs: "none", sm: "flex" } } }}
          onRowsPerPageChange={(event) => {
            setPerPage(Number(event.target.value));
            setPage(0);
          }}
        />
      ) : null}
    </Box>
  );
}

export default DataTable;
