{#-
  Use a model's +schema config verbatim instead of dbt's default
  "<target_schema>_<custom_schema>" concatenation, so silver models land in
  schema `silver` and gold models in `gold` — the three-schema medallion layout
  the README promises. Models with no +schema fall back to the target schema.
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
