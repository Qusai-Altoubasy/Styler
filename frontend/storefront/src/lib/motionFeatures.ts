/**
 * Motion's animation engine (layout, drag, gestures), loaded after the first page so
 * it stays out of the main bundle. Components use the small `m` element; LazyMotion
 * in main.tsx plugs this in.
 */
export { domMax as default } from "motion/react";
