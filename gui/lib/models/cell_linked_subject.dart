/// Subject linked to a map cell, enriched with title/status/direction from subject_subjects.
class CellLinkedSubject {
  final int cellSubjectId; // map_cell_subjects.id
  final int subjectId;
  final String title;
  final String status;   // open | resolved | superseded | abandoned
  final String direction; // mj_to_pj | pj_to_mj

  const CellLinkedSubject({
    required this.cellSubjectId,
    required this.subjectId,
    required this.title,
    required this.status,
    required this.direction,
  });
}
