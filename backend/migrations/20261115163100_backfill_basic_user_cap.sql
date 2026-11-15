-- Ensure every api_group includes PUR_CAP_BASIC_USER (CSV capabilities).
UPDATE api_group
SET capabilities = CASE
    WHEN capabilities IS NULL OR BTRIM(capabilities) = '' THEN 'PUR_CAP_BASIC_USER'
    WHEN ',' || capabilities || ',' LIKE '%,PUR_CAP_BASIC_USER,%' THEN capabilities
    ELSE capabilities || ',PUR_CAP_BASIC_USER'
END
WHERE capabilities IS NULL
   OR BTRIM(capabilities) = ''
   OR ',' || capabilities || ',' NOT LIKE '%,PUR_CAP_BASIC_USER,%';
