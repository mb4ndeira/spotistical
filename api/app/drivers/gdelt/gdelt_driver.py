from __future__ import annotations

import logging
from datetime import date
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# Queries temáticas que cobrem os 3 drivers de charts:
#   1. música/entretenimento  — causa direta de movimentação
#   2. esportes               — eventos correlacionam com comportamento de escuta
#   3. macro-economia         — driver de humor coletivo (Tier 3)
THEMES = [
    ("music",   "(music OR concert OR album OR singer OR band OR spotify OR streaming)"),
    ("sports",  "theme:SPORTS"),
    ("economy", "theme:ECON"),
]

# Mapeamento FIPS (GDELT sourcecountry) → ISO 3166-1 alpha-2
# GDELT usa os 2 primeiros caracteres do nome do país em inglês (mixed-case).
# Casos confirmados via inspeção de títulos/idiomas:
#   Un=United States, Ch=China, Au=Australia, Ta=Taiwan, So=South Korea
# Casos ambíguos marcados com comentário.
FIPS_TO_ISO: dict[str, str] = {
    "Al": "AL",  # Albania
    "An": "AO",  # Angola (Angola>Andorra por volume de notícias)
    "Ar": "AR",  # Argentina
    "Au": "AU",  # Australia
    "Az": "AZ",  # Azerbaijan
    "Ba": "BH",  # Bahrain (ambíguo: Bahrain ou Bosnia)
    "Be": "BE",  # Belgium
    "Bo": "BO",  # Bolivia
    "Br": "BR",  # Brazil
    "Bu": "BG",  # Bulgaria (FIPS BU → ISO BG)
    "Ca": "CA",  # Canada
    "Ch": "CN",  # China (confirmado via artigos em chinês)
    "Co": "CO",  # Colombia (confirmado via artigos em espanhol sobre Cartagena)
    "Cr": "CR",  # Costa Rica
    "Cu": "CU",  # Cuba
    "Cy": "CY",  # Cyprus
    "Cz": "CZ",  # Czech Republic
    "De": "DK",  # Denmark (Germany = "Ge" neste sistema)
    "Do": "DO",  # Dominican Republic
    "Ec": "EC",  # Ecuador
    "Eg": "EG",  # Egypt
    "El": "SV",  # El Salvador
    "Fi": "FI",  # Finland
    "Fr": "FR",  # France
    "Ge": "DE",  # Germany
    "Gh": "GH",  # Ghana
    "Gr": "GR",  # Greece
    "Gu": "GT",  # Guatemala
    "Ho": "HN",  # Honduras
    "Hu": "HU",  # Hungary
    "Ic": "IS",  # Iceland
    "In": "IN",  # India
    "Ir": "IR",  # Iran
    "Is": "IL",  # Israel (FIPS IS → ISO IL)
    "It": "IT",  # Italy
    "Ja": "JP",  # Japan (FIPS JA → ISO JP)
    "Jo": "JO",  # Jordan
    "Ke": "KE",  # Kenya
    "Ko": "KR",  # South Korea (ambíguo: Ko poderia ser Kosovo XK)
    "Ku": "KW",  # Kuwait
    "La": "LA",  # Laos
    "Le": "LB",  # Lebanon
    "Li": "LY",  # Libya (ambíguo: Lithuania=LT, Liechtenstein=LI)
    "Lu": "LU",  # Luxembourg
    "Ma": "MY",  # Malaysia (ambíguo: Morocco=MA)
    "Me": "MX",  # Mexico
    "Mo": "MA",  # Morocco
    "Ne": "NL",  # Netherlands
    "Ni": "NG",  # Nigeria (ambíguo: Nicaragua=NI)
    "No": "NO",  # Norway
    "Pa": "PA",  # Panama
    "Pe": "PE",  # Peru
    "Ph": "PH",  # Philippines
    "Po": "PL",  # Poland (ambíguo: Portugal=PT)
    "Qa": "QA",  # Qatar
    "Ro": "RO",  # Romania
    "Ru": "RU",  # Russia
    "Sa": "SA",  # Saudi Arabia
    "Se": "RS",  # Serbia (Sweden = "Sw" neste sistema)
    "Si": "SG",  # Singapore (ambíguo: Slovenia=SI)
    "Sl": "SK",  # Slovakia (ambíguo: Slovenia=SI, Sierra Leone=SL)
    "So": "KR",  # South Korea (confirmado via artigos em coreano sobre Ansan)
    "Sp": "ES",  # Spain
    "Sr": "LK",  # Sri Lanka
    "Su": "SD",  # Sudan
    "Sw": "SE",  # Sweden
    "Sy": "SY",  # Syria
    "Ta": "TW",  # Taiwan (confirmado via artigos em chinês sobre Jolin Tsai)
    "Th": "TH",  # Thailand
    "Tu": "TR",  # Turkey
    "Uk": "UA",  # Ukraine
    "Un": "US",  # United States (confirmado — maior volume)
    "Ur": "UY",  # Uruguay
    "Ve": "VE",  # Venezuela
    "Vi": "VN",  # Vietnam
    "Ye": "YE",  # Yemen
    "Zi": "ZW",  # Zimbabwe
}


class GdeltDriver:
    """Acessa o GDELT DOC API 2.0 — sem autenticação.

    Rate limit documentado: 1 request a cada 5 segundos.
    Retorna até 250 artigos por request.
    Usa sort=ToneDesc para garantir que o campo `tone` venha na resposta.
    """

    async def fetch_articles(
        self,
        *,
        date_from: date,
        date_to: date,
        query: str,
        client: httpx.AsyncClient,
        max_records: int = 250,
    ) -> list[dict[str, Any]]:
        params = {
            "query":         query,
            "mode":          "ArtList",
            "maxrecords":    str(max_records),
            "format":        "json",
            "sort":          "ToneDesc",   # força o campo tone na resposta
            "startdatetime": date_from.strftime("%Y%m%d") + "000000",
            "enddatetime":   date_to.strftime("%Y%m%d") + "235959",
        }

        logger.info("GdeltDriver: %s  %s → %s", query[:40], date_from, date_to)

        resp = await client.get(_BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for a in (data.get("articles") or []):
            seendate = a.get("seendate", "")
            try:
                from datetime import datetime
                pub = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ")
            except (ValueError, TypeError):
                continue

            fips    = (a.get("sourcecountry") or "")[:2] or None
            iso     = FIPS_TO_ISO.get(fips) if fips else None
            raw_tone = a.get("tone")
            try:
                tone = float(raw_tone) if raw_tone is not None else None
            except (ValueError, TypeError):
                tone = None

            results.append({
                "published_at": pub,
                "title":        (a.get("title") or "")[:1024],
                "url":          (a.get("url")   or "")[:2048],
                "country":      iso,
                "tone":         tone,
                "source_lang":  a.get("language") or None,
            })

        logger.info("GdeltDriver: %d artigos recebidos", len(results))
        return results


gdelt_driver = GdeltDriver()
