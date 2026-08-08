/**
 * Shared UI kit. Pages import from here, not from raw MUI, whenever a wrapper
 * exists — so layout and spacing stay consistent without restyling per page.
 */

export { PageContainer } from "./PageContainer";
export type { PageContainerProps } from "./PageContainer";
export { SectionCard } from "./SectionCard";
export type { SectionCardProps } from "./SectionCard";
export { Pill } from "./Pill";
export type { PillProps } from "./Pill";
export { TabBar } from "./TabBar";
export type { TabBarProps, TabItem } from "./TabBar";
export { Placeholder } from "./Placeholder";
export type { PlaceholderProps } from "./Placeholder";
export { timestampSx, FRAME_LABEL_WIDTH, FRAME_NUMBER_WIDTH } from "./timestamps";
export { palette, grays, semantic, surface, handColors } from "./palette";
export type { ColorAlias, Shade } from "./palette";
export { theme } from "./theme";
