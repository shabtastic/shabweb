import path from 'path';

const HOME = process.env.HOME;

/**
 * Directories the corpus pipeline scans for matching documents.
 * Order is not meaningful; all roots are walked recursively.
 */
export const ROOTS = [
  path.join(HOME, 'Downloads/fromSugarSync'),
  path.join(HOME, 'Downloads/Projects'),
  path.join(HOME, 'Downloads/Project Archive'),
  path.join(HOME, 'Downloads/fromInternet'),
];
