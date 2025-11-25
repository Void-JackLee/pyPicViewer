def calc_F_number(fstr):
    fstr = str(fstr)
    idx = fstr.find('/')
    if idx == -1:
        return fstr
    a = fstr[:idx]
    b = fstr[idx+1:]
    return f'{float(a)/float(b):.1f}'
