/**
 * The shared components and the design tokens (implementation 02, plan section 7.4). Pages draw a
 * title, a button, a list, a table, a toolbox, an empty state or a confirmation only through these,
 * so the same job looks the same on every screen.
 */

export { AppShell, PageBody } from "./AppShell";
export type { AppShellProps } from "./AppShell";
export { Sidebar } from "./Sidebar";
export type { SidebarGroup, SidebarItem, SidebarProps } from "./Sidebar";
export { PageHeader } from "./PageHeader";
export type { PageHeaderProps } from "./PageHeader";
export { Section } from "./Section";
export type { SectionProps } from "./Section";
export { IconAction } from "./IconAction";
export type { IconActionProps } from "./IconAction";
export { PillButton } from "./PillButton";
export type { PillButtonProps } from "./PillButton";
export { Segmented } from "./Segmented";
export type { SegmentedOption, SegmentedProps } from "./Segmented";
export { ListRow } from "./ListRow";
export type { ListRowProps } from "./ListRow";
export { RowMenu } from "./RowMenu";
export type { RowMenuItem, RowMenuProps } from "./RowMenu";
export { DataTable } from "./DataTable";
export type { DataColumn, DataTableProps } from "./DataTable";
export { EmptyState } from "./EmptyState";
export type { EmptyStateProps } from "./EmptyState";
export { ConfirmDialog } from "./ConfirmDialog";
export type { ConfirmDialogProps } from "./ConfirmDialog";
export { Toolbox } from "./Toolbox";
export type { ToolboxProps } from "./Toolbox";
export { FloatingBar } from "./FloatingBar";
export type { FloatingBarProps } from "./FloatingBar";
export { MiniPiano } from "./MiniPiano";
export type { MiniPianoProps } from "./MiniPiano";
export { FigurePicker } from "./FigurePicker";
export type { FigurePickerProps } from "./FigurePicker";
export { StepTabs } from "./StepTabs";
export type { StepItem, StepState, StepTabsProps } from "./StepTabs";
export { Pill } from "./Pill";
export type { PillProps } from "./Pill";
export { TabBar } from "./TabBar";
export type { TabBarProps, TabItem } from "./TabBar";
export { timestampSx, FRAME_LABEL_WIDTH, FRAME_NUMBER_WIDTH } from "./timestamps";
export { progressSx, PROGRESS_MAX_WIDTH } from "./progress";
export { relativeTime, fullTime } from "./relativeTime";
export { palette, grays, semantic, handColors } from "./palette";
export type { ColorAlias, Shade } from "./palette";
export { ui, lightTokens, darkTokens, fontFamily, fontSize, radius, shadow, size } from "./tokens";
export type { Tokens } from "./tokens";
export { theme } from "./theme";
