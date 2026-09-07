"""Oracle-free indicator stopping."""
def indicator_stop(eta,k,threshold=1e-3):
    return eta/(abs(k)+1e-8)<threshold
