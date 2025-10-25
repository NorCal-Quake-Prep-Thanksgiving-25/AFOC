"""Legal protection automation for EliteAI commercial assets."""

from __future__ import annotations

import logging
from typing import Sequence

from afoc.datatypes import CommercialLicense


class LegalProtectionAutomation:
    """Generates legal artefacts that safeguard commercial IP."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.default_restrictions: Sequence[str] = (
            "No redistribution without express written permission",
            "No reverse engineering or decompilation",
            "No commercial use without license",
            "Automatic legal action on IP theft",
        )

    def generate_commercial_license(self) -> CommercialLicense:
        license_doc = CommercialLicense(
            copyright="© 2024 EliteAI Enterprises. All Rights Reserved.",
            restrictions=list(self.default_restrictions),
            enforcement="Digital Millennium Copyright Act compliance",
            jurisdiction="International IP law protection",
        )
        self.logger.debug("Generated commercial license: %s", license_doc)
        return license_doc

    def generate_headers(self, modules: Sequence[str]) -> str:
        header = "; ".join(
            f"Module {name} protected by EliteAI commercial license" for name in modules
        )
        self.logger.debug("Generated legal headers for modules: %s", modules)
        return header
