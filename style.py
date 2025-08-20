

def format_euro(valor):
    return f"{valor:,.2f} €".replace(",","X").replace(".",",").replace("X",".")

def format_perc(valor):
    return f"{valor:,.2f} %".replace(",","X").replace(".",",").replace("X",".")

def format_titol(valor):
    return f"{valor:,.0f} €".replace(",","X").replace(".",",").replace("X",".")
