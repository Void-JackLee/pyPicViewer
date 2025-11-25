def calc_exif_number(fstr, number=1):
    fstr = str(fstr)
    idx = fstr.find('/')
    if idx == -1:
        return fstr
    a = fstr[:idx]
    b = fstr[idx+1:]
    return f'{float(a)/float(b):.{number}f}'
