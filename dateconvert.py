"Takes DD.MM.YYYY and returns YYYY-MM-DD"
def rapladate_to_iso(date):
    date = date.split('.')
    return "{}-{}-{}".format(date[2], date[1], date[0])
