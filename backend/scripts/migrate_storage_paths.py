"""Rewrite persisted Windows storage paths for a Linux container deployment."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database.mysql_db import (  # noqa: E402
    ChatMessage,
    ClassMaterial,
    HomeworkAssignment,
    HomeworkAttachment,
    HomeworkSubmission,
    HomeworkSubmissionAttachment,
    RagDocumentSource,
    SessionLocal,
)


PATH_COLUMNS = (
    (ClassMaterial, "file_path", False),
    (HomeworkAssignment, "attachment_path", False),
    (HomeworkAttachment, "file_path", False),
    (HomeworkSubmission, "file_path", False),
    (HomeworkSubmissionAttachment, "file_path", False),
    (ChatMessage, "image_path", True),
    (RagDocumentSource, "file_path", False),
)


class PathMigrationError(ValueError):
    pass


def _relative_storage_path(value: str) -> PurePosixPath:
    normalized = value.strip().replace("\\", "/")
    lowered = normalized.casefold()
    marker = "/storage/"
    marker_index = lowered.rfind(marker)
    if marker_index < 0:
        raise PathMigrationError("path is not inside a recognizable storage directory")

    relative = PurePosixPath(normalized[marker_index + len(marker):])
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise PathMigrationError("path contains an unsafe storage-relative component")
    return relative


def _validate_target(storage_root: Path, relative: PurePosixPath) -> Path:
    target = storage_root.joinpath(*relative.parts).resolve()
    try:
        target.relative_to(storage_root)
    except ValueError as exc:
        raise PathMigrationError("resolved path escapes the storage root") from exc
    if not target.is_file():
        raise PathMigrationError(f"target file is missing: {target}")
    return target


def rewrite_storage_path(
    value: str,
    *,
    storage_root: Path,
    chat_image: bool = False,
) -> str:
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        return value

    if chat_image and not (
        normalized.startswith("/")
        or (len(normalized) >= 3 and normalized[1:3] == ":/")
    ):
        relative_chat = PurePosixPath(normalized)
        if relative_chat.is_absolute() or ".." in relative_chat.parts:
            raise PathMigrationError("chat image path is unsafe")
        _validate_target(
            storage_root,
            PurePosixPath("raw", "chat_images", *relative_chat.parts),
        )
        return relative_chat.as_posix()

    relative = _relative_storage_path(normalized)
    target = _validate_target(storage_root, relative)

    if chat_image:
        prefix = PurePosixPath("raw", "chat_images")
        try:
            return PurePosixPath(*target.relative_to(storage_root).parts).relative_to(
                prefix
            ).as_posix()
        except ValueError as exc:
            raise PathMigrationError(
                "chat image path is not inside storage/raw/chat_images"
            ) from exc

    return target.as_posix()


def migrate(*, storage_root: Path, apply_changes: bool) -> int:
    storage_root = storage_root.resolve()
    if not storage_root.is_dir():
        raise PathMigrationError(f"storage root does not exist: {storage_root}")

    session = SessionLocal()
    pending: list[tuple[object, str, str]] = []
    errors: list[str] = []
    inspected = 0

    try:
        for model, field_name, chat_image in PATH_COLUMNS:
            field = getattr(model, field_name)
            rows = session.query(model).filter(field.isnot(None), field != "").all()
            for row in rows:
                inspected += 1
                current = getattr(row, field_name)
                try:
                    rewritten = rewrite_storage_path(
                        current,
                        storage_root=storage_root,
                        chat_image=chat_image,
                    )
                except PathMigrationError as exc:
                    errors.append(
                        f"{model.__tablename__} id={row.id} {field_name}: {exc}"
                    )
                    continue
                if rewritten != current:
                    pending.append((row, field_name, rewritten))
                    print(
                        f"rewrite {model.__tablename__} id={row.id} "
                        f"{field_name} -> {rewritten}"
                    )

        print(
            f"inspected={inspected} rewrites={len(pending)} errors={len(errors)}"
        )
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)

        if errors:
            session.rollback()
            return 1

        if apply_changes:
            for row, field_name, rewritten in pending:
                setattr(row, field_name, rewritten)
            session.commit()
            print("storage path migration committed")
        else:
            session.rollback()
            print("dry run only; no database changes were made")
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/app/storage"),
        help="Storage root visible to the backend process",
    )
    args = parser.parse_args()
    try:
        return migrate(storage_root=args.root, apply_changes=args.apply)
    except PathMigrationError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
