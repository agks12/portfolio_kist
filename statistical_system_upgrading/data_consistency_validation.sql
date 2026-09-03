-- 서로 다른 두 데이터 소스의 집계 값을 비교하여 차이를 분석하는 예제
-- (엑셀 데이터 vs GIS 데이터)
-- 본 코드는 회사 보안 정책 및 민감한 비즈니스 로직 보호를 위해, 실제 사용된 테이블명, 컬럼명 및 일부 조건식은 **가상의 이름(Sample Schema)으로 마스킹(대체)하여 업로드**되었습니다. 
-- 전체적인 파이프라인 구조와 검증 아키텍처 흐름 위주로 참고해 주시기 바랍니다.


WITH source_a_agg AS (
    -- Source A: 시스템 기반 집계 데이터
    SELECT 
        a.batch_id,
        a.region_lv1,
        a.region_lv2,
        a.category,
        SUM(a.metric_1) AS a_metric_1,
        SUM(a.metric_2) AS a_metric_2,
        SUM(a.metric_3) AS a_metric_3,
        SUM(a.metric_1) - SUM(a.metric_2) AS a_net_metric,
        SUM(a.metric_1) + SUM(a.metric_3) AS a_total_metric
    FROM sample_schema.source_a_detail a
    WHERE a.version_flag = 1
    GROUP BY a.batch_id, a.region_lv1, a.region_lv2, a.category
),

source_b_agg AS (
    -- Source B: 외부/분석 데이터
    WITH base_metric AS (
        SELECT 
            b.batch_id,
            b.region_lv2,
            b.category_main,
            SUM(b.metric_main) AS b_metric_main
        FROM sample_schema.source_b_data b
        WHERE 
            (
                RIGHT(b.batch_id, 2) = 'XX'
                AND b.version_flag = 3
            )
            OR
            (
                RIGHT(b.batch_id, 2) <> 'XX'
                AND b.version_flag = 1
            )
        GROUP BY b.batch_id, b.region_lv2, b.category_main
    ),
    extra_metric AS (
        SELECT 
            b.batch_id,
            b.region_lv2,
            b.category_sub,
            SUM(b.metric_sub) AS b_metric_sub
        FROM sample_schema.source_b_data b
        WHERE 
            (
                RIGHT(b.batch_id, 2) = 'XX'
                AND b.version_flag = 3
            )
            OR
            (
                RIGHT(b.batch_id, 2) <> 'XX'
                AND b.version_flag = 1
            )
        GROUP BY b.batch_id, b.region_lv2, b.category_sub
    )
    SELECT
        bm.batch_id,
        bm.region_lv2,
        bm.category_main,
        bm.b_metric_main,
        em.b_metric_sub,
        COALESCE(bm.b_metric_main, 0) 
        + COALESCE(em.b_metric_sub, 0) AS b_total_metric
    FROM base_metric bm
    LEFT JOIN extra_metric em
        ON bm.batch_id = em.batch_id
        AND bm.region_lv2 = em.region_lv2
        AND bm.category_main = em.category_sub
),

final_comparison AS (
    SELECT 
        sa.batch_id,
        sa.region_lv2,
        sa.category,

        -- Source A
        sa.a_metric_1,
        sa.a_metric_3,
        sa.a_total_metric,

        -- Source B
        sb.b_metric_main,
        sb.b_metric_sub,
        sb.b_total_metric,

        -- 차이 계산 (floating point 안정성 고려)
        CASE
            WHEN ABS(
                COALESCE(sa.a_metric_1, 0) 
              - COALESCE(sb.b_metric_main, 0)
            ) < 1e-9 THEN 0
            ELSE COALESCE(sa.a_metric_1, 0) 
               - COALESCE(sb.b_metric_main, 0)
        END AS diff_main_metric,

        COALESCE(sa.a_metric_3, 0) 
      - COALESCE(sb.b_metric_sub, 0) AS diff_sub_metric,

        COALESCE(sa.a_total_metric, 0) 
      - COALESCE(sb.b_total_metric, 0) AS diff_total_metric

    FROM source_a_agg sa
    JOIN source_b_agg sb
        ON sa.batch_id = sb.batch_id
        AND sa.region_lv2 = sb.region_lv2
        AND (
            sa.category = sb.category_main
            OR (sa.category = 'category_variant_1' AND sb.category_main = 'category_base_1')
            OR (sa.category = 'category_variant_2' AND sb.category_main = 'category_base_2')
        )
)

SELECT *
FROM final_comparison
ORDER BY batch_id, region_lv2, category;
