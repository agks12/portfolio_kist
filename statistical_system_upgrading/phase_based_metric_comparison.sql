-- Multi-stage lifecycle data normalization and comparison pipeline
-- (phase generation → forward fill → delta calculation → cross-source validation)

WITH base_schedule AS (
    -- 기준 이벤트에서 phase 생성
    SELECT
        batch_id,
        entity_id,
        period_label,
        (REPLACE(period_label, 'P', '')::int - 1) AS phase,
        category_code,
        category_name,
        CASE
            WHEN category_name IN ('type_a1','type_a2') THEN 'type_a'
            WHEN category_name IN ('type_b1','type_b2') THEN 'type_b'
            ELSE category_name
        END AS category_group
    FROM sample_schema.schedule_table
),

expanded_phase AS (
    -- 각 entity별 1~N phase 확장
    SELECT
        batch_id,
        entity_id,
        category_group,
        generate_series(1, 5) AS phase
    FROM base_schedule
    WHERE period_label IS NOT NULL
    GROUP BY batch_id, entity_id, category_group
),

phase_filled AS (
    -- 기존 phase와 매핑
    SELECT
        e.batch_id,
        e.entity_id,
        e.phase,
        e.category_group,
        b.period_label,
        b.category_code,
        b.category_name
    FROM expanded_phase e
    LEFT JOIN base_schedule b
        ON e.batch_id = b.batch_id
        AND e.entity_id = b.entity_id
        AND e.phase = b.phase
        AND e.category_group = b.category_group
),

phase_grouping AS (
    -- forward fill을 위한 그룹 생성
    SELECT
        *,
        SUM(CASE WHEN period_label IS NOT NULL THEN 1 ELSE 0 END)
        OVER (PARTITION BY batch_id, entity_id, category_group ORDER BY phase) AS grp
    FROM phase_filled
),

normalized_schedule AS (
    -- 결측값 채우기 (forward fill)
    SELECT
        batch_id,
        entity_id,
        phase,
        category_group,
        MAX(category_code) OVER (PARTITION BY batch_id, entity_id, category_group, grp ORDER BY phase) AS category_code,
        MAX(category_name) OVER (PARTITION BY batch_id, entity_id, category_group, grp ORDER BY phase) AS category_name,
        MAX(period_label) OVER (PARTITION BY batch_id, entity_id, category_group ORDER BY phase) AS period_label
    FROM phase_grouping
),

status_data AS (
    -- 상태 데이터 (예: 잔여값)
    SELECT
        *,
        CASE
            WHEN category_name IN ('type_a1','type_a2') THEN 'type_a'
            WHEN category_name IN ('type_b1','type_b2') THEN 'type_b'
            ELSE category_name
        END AS category_group
    FROM sample_schema.status_table
),

joined_status AS (
    -- 스케줄 + 상태 데이터 결합
    SELECT
        ns.batch_id,
        ns.entity_id,
        ns.phase,
        ns.period_label,
        ns.category_name,
        ns.category_group,
        s.status_flag,
        s.value_current,
        LAG(s.value_current) OVER (
            PARTITION BY ns.batch_id, ns.entity_id, ns.category_group
            ORDER BY ns.phase
        ) AS prev_value
    FROM normalized_schedule ns
    JOIN status_data s
        ON ns.batch_id = s.batch_id
        AND ns.entity_id = s.entity_id
        AND ns.phase = s.phase
        AND ns.category_group = s.category_group
),

aggregated_source_a AS (
    -- Source A 집계 (잔여 + delta 계산)
    SELECT
        batch_id,
        region,
        phase,
        period_label,
        category_name,
        SUM(value_current) AS current_value,
        CASE
            WHEN phase = 1 THEN NULL
            ELSE LAG(SUM(value_current)) OVER (
                PARTITION BY batch_id, region, category_name
                ORDER BY phase
            ) - SUM(value_current)
        END AS delta_value
    FROM joined_status
    GROUP BY batch_id, region, phase, period_label, category_name
),

aggregated_source_b AS (
    -- Source B (다른 데이터 소스)
    SELECT
        batch_id,
        region,
        phase,
        period_label,
        category_name,
        SUM(metric_value) AS current_value,
        CASE
            WHEN phase = 1 THEN NULL
            ELSE LAG(SUM(metric_value)) OVER (
                PARTITION BY batch_id, region, category_name
                ORDER BY phase
            ) - SUM(metric_value)
        END AS delta_value
    FROM sample_schema.external_detail
    GROUP BY batch_id, region, phase, period_label, category_name
),

final_comparison AS (
    -- 두 소스 비교
    SELECT
        a.batch_id,
        a.region,
        a.phase,
        a.period_label,
        a.category_name,

        a.current_value AS source_a_current,
        b.current_value AS source_b_current,

        a.delta_value AS source_a_delta,
        b.delta_value AS source_b_delta,

        ROUND(COALESCE(a.current_value, 0) - COALESCE(b.current_value, 0), 9) AS diff_current,
        ROUND(COALESCE(a.delta_value, 0) - COALESCE(b.delta_value, 0), 9) AS diff_delta

    FROM aggregated_source_a a
    JOIN aggregated_source_b b
        ON a.batch_id = b.batch_id
        AND a.region = b.region
        AND a.phase = b.phase
        AND a.period_label = b.period_label
        AND a.category_name = b.category_name
)

SELECT *
FROM final_comparison
ORDER BY batch_id, region, phase, category_name;
