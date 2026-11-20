"""Paginated saved reconciliations, including records outside the state preview."""

from datetime import date


def closing_history(connection, selected_date="", page="1"):
    if selected_date:
        try:
            if date.fromisoformat(selected_date).isoformat() != selected_date:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError("Choose a valid closing date")
    if (
        not isinstance(page, str)
        or not page.isascii()
        or not page.isdigit()
        or not 1 <= int(page) <= 1000000
    ):
        raise ValueError("Invalid history page")
    page_number = int(page)
    page_size = 10
    date_expression = (
        "COALESCE(c.business_date,date(c.created,'+6 hours','+30 minutes'))"
    )
    where = f"WHERE {date_expression}=?" if selected_date else ""
    parameters = (selected_date,) if selected_date else ()
    total = connection.execute(
        f"SELECT count(*) FROM closings c {where}", parameters
    ).fetchone()[0]
    records = connection.execute(
        f"SELECT c.*,u.name staff_name,{date_expression} closing_date FROM closings c JOIN users u ON u.id=c.staff {where} ORDER BY closing_date DESC,c.id DESC LIMIT ? OFFSET ?",
        (*parameters, page_size, (page_number - 1) * page_size),
    ).fetchall()
    return dict(
        records=[dict(record) for record in records],
        total=total,
        page=page_number,
        page_size=page_size,
    )
