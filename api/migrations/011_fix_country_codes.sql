-- ─────────────────────────────────────────────────────────────────
-- spotistical · normalizar country em news_events para ISO 3166-1
--
-- O GDELT DOC API retorna sourcecountry como os 2 primeiros caracteres
-- do nome do país em inglês (ex: "Un"=US, "Ch"=CN, "Sp"=ES).
-- Esta migration converte os registros existentes para ISO.
-- Artigos do Alpha Vantage (country IS NULL) não são afetados.
-- Casos confirmados via inspeção de títulos e idiomas dos artigos.
-- idempotent — safe to re-run.
-- ─────────────────────────────────────────────────────────────────

UPDATE news_events SET country = CASE country
    WHEN 'Al' THEN 'AL'  -- Albania
    WHEN 'An' THEN 'AO'  -- Angola
    WHEN 'Ar' THEN 'AR'  -- Argentina
    WHEN 'Au' THEN 'AU'  -- Australia
    WHEN 'Az' THEN 'AZ'  -- Azerbaijan
    WHEN 'Ba' THEN 'BH'  -- Bahrain
    WHEN 'Be' THEN 'BE'  -- Belgium
    WHEN 'Bo' THEN 'BO'  -- Bolivia
    WHEN 'Br' THEN 'BR'  -- Brazil
    WHEN 'Bu' THEN 'BG'  -- Bulgaria
    WHEN 'Ca' THEN 'CA'  -- Canada
    WHEN 'Ch' THEN 'CN'  -- China
    WHEN 'Co' THEN 'CO'  -- Colombia
    WHEN 'Cr' THEN 'CR'  -- Costa Rica
    WHEN 'Cu' THEN 'CU'  -- Cuba
    WHEN 'Cy' THEN 'CY'  -- Cyprus
    WHEN 'Cz' THEN 'CZ'  -- Czech Republic
    WHEN 'De' THEN 'DK'  -- Denmark
    WHEN 'Do' THEN 'DO'  -- Dominican Republic
    WHEN 'Ec' THEN 'EC'  -- Ecuador
    WHEN 'Eg' THEN 'EG'  -- Egypt
    WHEN 'El' THEN 'SV'  -- El Salvador
    WHEN 'Fi' THEN 'FI'  -- Finland
    WHEN 'Fr' THEN 'FR'  -- France
    WHEN 'Ge' THEN 'DE'  -- Germany
    WHEN 'Gh' THEN 'GH'  -- Ghana
    WHEN 'Gr' THEN 'GR'  -- Greece
    WHEN 'Gu' THEN 'GT'  -- Guatemala
    WHEN 'Ho' THEN 'HN'  -- Honduras
    WHEN 'Hu' THEN 'HU'  -- Hungary
    WHEN 'Ic' THEN 'IS'  -- Iceland
    WHEN 'In' THEN 'IN'  -- India
    WHEN 'Ir' THEN 'IR'  -- Iran
    WHEN 'Is' THEN 'IL'  -- Israel
    WHEN 'It' THEN 'IT'  -- Italy
    WHEN 'Ja' THEN 'JP'  -- Japan
    WHEN 'Jo' THEN 'JO'  -- Jordan
    WHEN 'Ke' THEN 'KE'  -- Kenya
    WHEN 'Ko' THEN 'KR'  -- South Korea
    WHEN 'Ku' THEN 'KW'  -- Kuwait
    WHEN 'La' THEN 'LA'  -- Laos
    WHEN 'Le' THEN 'LB'  -- Lebanon
    WHEN 'Li' THEN 'LY'  -- Libya
    WHEN 'Lu' THEN 'LU'  -- Luxembourg
    WHEN 'Ma' THEN 'MY'  -- Malaysia
    WHEN 'Me' THEN 'MX'  -- Mexico
    WHEN 'Mo' THEN 'MA'  -- Morocco
    WHEN 'Ne' THEN 'NL'  -- Netherlands
    WHEN 'Ni' THEN 'NG'  -- Nigeria
    WHEN 'No' THEN 'NO'  -- Norway
    WHEN 'Pa' THEN 'PA'  -- Panama
    WHEN 'Pe' THEN 'PE'  -- Peru
    WHEN 'Ph' THEN 'PH'  -- Philippines
    WHEN 'Po' THEN 'PL'  -- Poland
    WHEN 'Qa' THEN 'QA'  -- Qatar
    WHEN 'Ro' THEN 'RO'  -- Romania
    WHEN 'Ru' THEN 'RU'  -- Russia
    WHEN 'Sa' THEN 'SA'  -- Saudi Arabia
    WHEN 'Se' THEN 'RS'  -- Serbia
    WHEN 'Si' THEN 'SG'  -- Singapore
    WHEN 'Sl' THEN 'SK'  -- Slovakia
    WHEN 'So' THEN 'KR'  -- South Korea (confirmado via artigos em coreano)
    WHEN 'Sp' THEN 'ES'  -- Spain
    WHEN 'Sr' THEN 'LK'  -- Sri Lanka
    WHEN 'Su' THEN 'SD'  -- Sudan
    WHEN 'Sw' THEN 'SE'  -- Sweden
    WHEN 'Sy' THEN 'SY'  -- Syria
    WHEN 'Ta' THEN 'TW'  -- Taiwan (confirmado via artigos em chinês/taiwanese)
    WHEN 'Th' THEN 'TH'  -- Thailand
    WHEN 'Tu' THEN 'TR'  -- Turkey
    WHEN 'Uk' THEN 'UA'  -- Ukraine
    WHEN 'Un' THEN 'US'  -- United States (confirmado — maior volume)
    WHEN 'Ur' THEN 'UY'  -- Uruguay
    WHEN 'Ve' THEN 'VE'  -- Venezuela
    WHEN 'Vi' THEN 'VN'  -- Vietnam
    WHEN 'Ye' THEN 'YE'  -- Yemen
    WHEN 'Zi' THEN 'ZW'  -- Zimbabwe
    ELSE country           -- mantém NULL (AV) e qualquer código já em ISO
END
WHERE country IS NOT NULL
  AND length(country) = 2
  AND country != upper(country);  -- só toca os mixed-case do GDELT
