-- Bronze: Raw petitions from UK Parliament API
-- No transformations, just pointing to source

{{
    config(
        materialized='view',
        tags=['bronze', 'petitions']
    )
}}

SELECT
    id,
    (payload->>'petition_id')::int AS petition_id,
    payload->>'action' AS action,
    payload->>'background' AS background,
    payload->>'status' AS status,
    (payload->>'signature_count')::int AS signature_count,
    (payload->>'created_at')::timestamp AS created_at,
    (payload->>'updated_at')::timestamp AS updated_at,
    payload->>'creator_name' AS creator_name,
    payload->'topics' AS topics,
    ingested_at
FROM {{ source('bronze', 'petition_events_raw') }}
