def extract_re_value(p, string, value):
    try:
        return re.match(p, string).group(value)
    except (IndexError, AttributeError):
        return None


def extract_mafile(mafiles):
    mafile = None
    if self.mafiles:
        mafiles = copy(self.mafiles)
        mafile = mafiles.pop()