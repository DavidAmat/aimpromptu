/**
 * A table to compare many records on the same fields (plan section 7.4, guidelines 5.4): a sticky
 * header, every meaningful column sortable, and the rows per page chosen by the reader.
 *
 * The table is sized by its content inside a scroll container, never stretched to the window, so
 * a wide screen does not open a hole in the middle of each row. A column that always truncates
 * (an id) gets a fixed `width`. Numbers are right-aligned with tabular figures.
 */

import { useMemo, useState, type ReactNode } from "react";
import Box from "@mui/material/Box";
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
}

export function DataTable<Row>({
  columns,
  rows,
  rowKey,
  onRowClick,
  initialSort,
  rowsPerPageOptions = [25, 50, 100],
  maxHeight = "70vh",
}: DataTableProps<Row>) {
  const [sort, setSort] = useState(initialSort ?? null);
  const [page, setPage] = useState(0);
  const [perPage, setPerPage] = useState(rowsPerPageOptions[0]);

  const sorted = useMemo(() => {
    const column = sort ? columns.find((one) => one.key === sort.key) : undefined;
    if (!sort || !column?.sortValue) return rows;
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
  }, [rows, columns, sort]);

  const visible = sorted.slice(page * perPage, page * perPage + perPage);

  // The page controls stay under the table, at its width, not at the far edge of the page.
  return (
    <Box sx={{ width: "fit-content", maxWidth: "100%" }}>
      <TableContainer sx={{ maxHeight, maxWidth: "100%" }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
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
                      direction={sort?.key === column.key ? sort.direction : "asc"}
                      onClick={() =>
                        setSort((current) =>
                          current?.key === column.key
                            ? { key: column.key, direction: current.direction === "asc" ? "desc" : "asc" }
                            : { key: column.key, direction: "asc" },
                        )
                      }
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
              >
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
      {rows.length > rowsPerPageOptions[0] ? (
        <TablePagination
          component="div"
          count={rows.length}
          page={page}
          onPageChange={(_event, next) => setPage(next)}
          rowsPerPage={perPage}
          rowsPerPageOptions={rowsPerPageOptions}
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
