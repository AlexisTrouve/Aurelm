/// Typed wrappers for map drag data.
/// Using distinct types prevents DragTarget<int> from accidentally
/// accepting both asset drops and pawn drops.

/// Carried by Draggable tiles in AssetPanel → dropped on CellDragTargetOverlay.
class MapAssetDrag {
  final int assetId;
  const MapAssetDrag(this.assetId);
}

/// Carried by LongPressDraggable pawn tokens → dropped on PawnDragTargetOverlay.
class MapPawnDrag {
  final int pawnId;
  const MapPawnDrag(this.pawnId);
}
