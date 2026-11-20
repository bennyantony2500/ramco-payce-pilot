CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS customers (
  customer_id text PRIMARY KEY, name text, tier text, region text,
  monthly_fee_usd numeric, employees_paid int);
CREATE TABLE IF NOT EXISTS tickets (
  tkt text PRIMARY KEY, source text, org_id text, user_ref text,
  title text, message text, cat text, prio text, state text,
  created timestamptz, first_reply_ts timestamptz, closed_ts timestamptz,
  history jsonb);
CREATE TABLE IF NOT EXISTS policy_chunks (
  id serial PRIMARY KEY, source text, doc_id text, region text, topic text,
  chunk text, effective_from date, effective_to date,
  embedding vector(768));  -- 768 assumes a Google text-embedding model; confirm tomorrow
