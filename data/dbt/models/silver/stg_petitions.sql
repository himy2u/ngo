-- Silver: Cleaned and validated petitions

{{
    config(
        materialized='table',
        tags=['silver', 'petitions']
    )
}}

WITH source AS (
    SELECT * FROM {{ ref('raw_petitions') }}
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY petition_id
            ORDER BY updated_at DESC
        ) AS row_num
    FROM source
),

cleaned AS (
    SELECT
        petition_id,
        TRIM(action) AS action,
        TRIM(COALESCE(background, '')) AS background,
        LOWER(status) AS status,
        GREATEST(signature_count, 0) AS signature_count,
        created_at,
        updated_at,
        creator_name,
        topics,
        ingested_at
    FROM deduplicated
    WHERE row_num = 1
      AND petition_id IS NOT NULL
      AND action IS NOT NULL
)

SELECT * FROM cleaned
