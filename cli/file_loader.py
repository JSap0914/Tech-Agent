"""
File loader for loading PRD and design documents from local filesystem.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)


class FileLoadError(Exception):
    """Exception raised when file loading fails."""
    pass


def load_prd(file_path: str) -> str:
    """
    Load PRD content from file.

    Args:
        file_path: Path to PRD file (markdown or text)

    Returns:
        PRD content as string

    Raises:
        FileLoadError: If file doesn't exist or can't be read
    """
    path = Path(file_path)

    if not path.exists():
        raise FileLoadError(f"PRD file not found: {file_path}")

    if not path.is_file():
        raise FileLoadError(f"PRD path is not a file: {file_path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip():
            raise FileLoadError(f"PRD file is empty: {file_path}")

        logger.info("prd_loaded", file_path=str(path), size=len(content))
        return content

    except UnicodeDecodeError as e:
        raise FileLoadError(f"Failed to decode PRD file (not UTF-8): {file_path}") from e
    except Exception as e:
        raise FileLoadError(f"Failed to read PRD file: {file_path}") from e


def load_design_docs(folder_path: str) -> Dict[str, str]:
    """
    Load design documents from folder.

    Expected structure:
        design-docs/
        ├── design_system.md (required)
        ├── ux_flow.md (required)
        ├── screen_specs.md (required)
        ├── wireframes.md (optional)
        └── component_library.md (optional)

    Args:
        folder_path: Path to folder containing design documents

    Returns:
        Dictionary mapping document type to content

    Raises:
        FileLoadError: If required files are missing
    """
    path = Path(folder_path)

    if not path.exists():
        raise FileLoadError(f"Design docs folder not found: {folder_path}")

    if not path.is_dir():
        raise FileLoadError(f"Design docs path is not a directory: {folder_path}")

    # Required documents
    required_docs = {
        "design_system": "design_system.md",
        "ux_flow": "ux_flow.md",
        "screen_specs": "screen_specs.md"
    }

    # Optional documents
    optional_docs = {
        "wireframes": "wireframes.md",
        "component_library": "component_library.md"
    }

    design_docs = {}

    # Load required documents
    for doc_type, filename in required_docs.items():
        file_path = path / filename

        if not file_path.exists():
            raise FileLoadError(
                f"Required design document missing: {filename}\n"
                f"Expected at: {file_path}"
            )

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                raise FileLoadError(f"Design document is empty: {filename}")

            design_docs[doc_type] = content
            logger.info("design_doc_loaded", type=doc_type, size=len(content))

        except UnicodeDecodeError as e:
            raise FileLoadError(f"Failed to decode {filename} (not UTF-8)") from e
        except Exception as e:
            raise FileLoadError(f"Failed to read {filename}") from e

    # Load optional documents
    for doc_type, filename in optional_docs.items():
        file_path = path / filename

        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if content.strip():
                    design_docs[doc_type] = content
                    logger.info("design_doc_loaded", type=doc_type, size=len(content))

            except Exception as e:
                logger.warning("design_doc_load_failed", type=doc_type, error=str(e))

    logger.info("design_docs_loaded", total=len(design_docs))
    return design_docs


def load_ai_studio_code(file_path: Optional[str]) -> Optional[str]:
    """
    Validate Google AI Studio code ZIP file path.

    Args:
        file_path: Path to ZIP file (optional)

    Returns:
        Validated file path or None

    Raises:
        FileLoadError: If file exists but is invalid
    """
    if not file_path:
        return None

    path = Path(file_path)

    if not path.exists():
        raise FileLoadError(f"AI Studio code file not found: {file_path}")

    if not path.is_file():
        raise FileLoadError(f"AI Studio code path is not a file: {file_path}")

    if path.suffix.lower() != '.zip':
        raise FileLoadError(f"AI Studio code file must be a ZIP archive: {file_path}")

    logger.info("ai_studio_code_validated", file_path=str(path), size=path.stat().st_size)
    return str(path.absolute())


def validate_inputs(
    prd_path: str,
    design_docs_path: str,
    ai_studio_code_path: Optional[str] = None
) -> Tuple[str, Dict[str, str], Optional[str]]:
    """
    Validate and load all input documents.

    Args:
        prd_path: Path to PRD file
        design_docs_path: Path to design documents folder
        ai_studio_code_path: Optional path to Google AI Studio ZIP

    Returns:
        Tuple of (prd_content, design_docs, ai_studio_code_path)

    Raises:
        FileLoadError: If any validation fails
    """
    logger.info("validating_inputs", prd=prd_path, design_docs=design_docs_path)

    # Load PRD
    prd_content = load_prd(prd_path)

    # Load design documents
    design_docs = load_design_docs(design_docs_path)

    # Validate AI Studio code if provided
    ai_studio_validated = load_ai_studio_code(ai_studio_code_path)

    logger.info(
        "inputs_validated",
        prd_size=len(prd_content),
        design_docs_count=len(design_docs),
        has_ai_studio_code=ai_studio_validated is not None
    )

    return prd_content, design_docs, ai_studio_validated
