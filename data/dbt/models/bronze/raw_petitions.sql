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
    (payload ->> 'petition_id')::int AS petition_id,
    (payload ->> 'signature_count')::int AS signature_count,
    (payload ->> 'created_at')::timestamp AS created_at,
    (payload ->> 'updated_at')::timestamp AS updated_at,
    ingested_at,
    payload ->> 'action' AS action,
    payload ->> 'background' AS background,
    payload ->> 'status' AS status,
    payload ->> 'creator_name' AS creator_name,
    payload -> 'topics' AS topics
FROM {{ source('bronze', 'petition_events_raw') }}
