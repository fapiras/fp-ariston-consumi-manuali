"""Synthetic two-channel wire reports; no captured household data."""
def wire(periods):
    return [
        {'k':kind, 'p':p, 'v':row['v'] if kind == 8 else [0]*len(row['v'])}
        for p,row in enumerate(periods,1) for kind in (8,9)
    ]
