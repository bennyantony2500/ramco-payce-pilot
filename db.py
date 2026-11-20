"""One connection per region. India = proxy on 5433, UAE = proxy on 5434."""
import os, psycopg
PORTS = {"IN": 5433, "UAE": 5434}

def connect(region):
    return psycopg.connect(host="127.0.0.1", port=PORTS[region], dbname="ramco", user="postgres",
                           password=os.environ["PGPASSWORD"], autocommit=True)

def vec(v):
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"
