from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.mysql_db import ClassMaterial, RagDocument, RagDocumentSource


def get_document_by_hash(db: Session, content_hash: str) -> Optional[RagDocument]:
    return db.query(RagDocument).filter(
        RagDocument.content_hash == content_hash,
    ).first()


def get_or_create_document(
    db: Session,
    content_hash: str,
    file_type: str,
    file_size: int,
) -> tuple[RagDocument, bool]:
    document = get_document_by_hash(db, content_hash)
    if document:
        return document, False
    document = RagDocument(
        content_hash=content_hash,
        file_type=file_type,
        file_size=file_size,
        index_status="pending",
    )
    db.add(document)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_document_by_hash(db, content_hash)
        if existing:
            return existing, False
        raise
    db.refresh(document)
    return document, True


def set_document_status(db: Session, document: RagDocument, status: str) -> None:
    document.index_status = status
    db.commit()
    db.refresh(document)


def get_material_source(
    db: Session, material_id: int
) -> Optional[RagDocumentSource]:
    return db.query(RagDocumentSource).filter(
        RagDocumentSource.material_id == material_id,
    ).first()


def get_global_source(
    db: Session, file_path: str
) -> Optional[RagDocumentSource]:
    return db.query(RagDocumentSource).filter(
        RagDocumentSource.scope_type == "global",
        RagDocumentSource.file_path == file_path,
    ).first()


def add_source(
    db: Session,
    document_id: int,
    scope_type: str,
    filename: str,
    file_path: str,
    class_id: int | None = None,
    material_id: int | None = None,
) -> RagDocumentSource:
    if material_id is not None:
        existing = get_material_source(db, material_id)
    else:
        existing = get_global_source(db, file_path)
    if existing:
        if existing.document_id != document_id:
            existing.document_id = document_id
            existing.filename = filename
            existing.class_id = class_id
            db.commit()
            db.refresh(existing)
        return existing
    source = RagDocumentSource(
        document_id=document_id,
        scope_type=scope_type,
        class_id=class_id,
        material_id=material_id,
        filename=filename,
        file_path=file_path,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def list_sources(db: Session, document_id: int) -> list[RagDocumentSource]:
    return db.query(RagDocumentSource).filter(
        RagDocumentSource.document_id == document_id,
    ).order_by(RagDocumentSource.id.asc()).all()


def serialize_sources(sources: list[RagDocumentSource]) -> list[dict]:
    return [
        {
            "scope_type": source.scope_type,
            "class_id": source.class_id,
            "material_id": source.material_id,
            "filename": source.filename,
        }
        for source in sources
    ]


def scope_keys(sources: list[RagDocumentSource]) -> list[str]:
    keys = set()
    for source in sources:
        if source.scope_type == "global":
            keys.add("global")
        elif source.class_id is not None:
            keys.add(f"class:{source.class_id}")
    return sorted(keys)


def remove_source(db: Session, source: RagDocumentSource) -> None:
    db.delete(source)
    db.commit()


def delete_document(db: Session, document: RagDocument) -> None:
    db.delete(document)
    db.commit()


def clear_registry(db: Session) -> None:
    db.query(RagDocumentSource).delete()
    db.query(RagDocument).delete()
    db.query(ClassMaterial).update({ClassMaterial.content_hash: None})
    db.commit()


def list_all_class_materials(db: Session) -> list[ClassMaterial]:
    return db.query(ClassMaterial).order_by(ClassMaterial.id.asc()).all()
