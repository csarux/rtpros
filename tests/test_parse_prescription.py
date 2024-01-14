import aclinprot as acp

Vxx_test = 'data/Vxx.csv'

def test_parse_prescription(prescription_test = Vxx_test):
    acp.parse_prescription(prescription_test)

