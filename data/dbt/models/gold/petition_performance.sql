-- Gold: Petition performance metrics

{{
    config(
        materialized='table',
        tags=['gold', 'petitions', 'metrics']
    )
}}

WITH petitions AS (
    SELECT * FROM {{ ref('stg_petitions') }}
),

metrics AS (
    SELECT
        petition_id,
        action,
        status,
        signature_count,
        created_at,
        updated_at,

        -- Derived metrics
        DATE(created_at) AS created_date,
        EXTRACT(EPOCH FROM (updated_at - created_at)) / 86400.0 AS days_active,

        CASE
            WHEN signature_count >= 100000 THEN 'viral'
            WHEN signature_count >= 10000 THEN 'popular'
            WHEN signature_count >= 1000 THEN 'growing'
            ELSE 'starting'
        END AS performance_tier,

        COALESCE(status IN ('responded', 'awaiting_response'), FALSE) AS government_engaged,

        -- Velocity (signatures per day)
        CASE
            WHEN EXTRACT(EPOCH FROM (updated_at - created_at)) > 0
                THEN
                    signature_count / (EXTRACT(EPOCH FROM (updated_at - created_at)) / 86400.0)
            ELSE 0
        END AS signatures_per_day

    FROM petitions
)

SELECT
    *,
    CURRENT_TIMESTAMP AS refreshed_at
FROM metrics
