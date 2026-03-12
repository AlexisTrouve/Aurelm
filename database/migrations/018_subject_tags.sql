-- Migration 018: Add tags to subjects
-- Auto-assigned by the pipeline during extraction (keyword matching on title+description).
-- Same domain vocabulary as entity tags: militaire, religieux, politique, economique,
-- culturel, diplomatique, technologique, mythologique.

ALTER TABLE subject_subjects ADD COLUMN tags TEXT DEFAULT '[]';
