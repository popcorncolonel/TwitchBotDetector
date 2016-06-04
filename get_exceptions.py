def get_exceptions():
    f = open("exceptions.txt")
    return [line.encode('string-escape') for line in f.read().splitlines() if (line != '' and line != '\n')]
