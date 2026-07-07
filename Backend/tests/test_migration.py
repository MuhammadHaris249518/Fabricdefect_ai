"""Verify the migration applied correctly."""
from sqlalchemy import text

from app.db.session import engine


def main():
    conn = engine.connect()
    r = conn.execute(
        text(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name='images' "
            "ORDER BY ordinal_position"
        )
    )
    print("images columns:")
    found = False
    for row in r:
        print(f"  {row[0]:30s} {row[1]:15s} nullable={row[2]}")
        if row[0] == "roboflow_image_id":
            found = True
    conn.close()

    if found:
        print("\n✓ roboflow_image_id column exists!")
    else:
        print("\n✗ roboflow_image_id column NOT found!")
        exit(1)


if __name__ == "__main__":
    main()