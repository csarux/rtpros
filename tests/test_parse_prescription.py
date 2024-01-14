import aclinprot as acp

Vxx_test = 'data/Vxx.csv'

def test_parse_prescription(prescription_test = Vxx_test):
    acp.parse_prescription(prescription_test)

# Parse Vxx type dosimetric parameter
def test_parseDosimPar_1(strDosimPar='V 36$42%'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Vxx%'] == {'VolumeRelative': 42.0, 'DoseGy': 36.0}
    
def test_parseDosimPar_2(strDosimPar='V36$42%'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Vxx%'] == {'VolumeRelative': 42.0, 'DoseGy': 36.0}
    
def test_parseDosimPar_3(strDosimPar='V 36$42 %'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Vxx%'] == {'VolumeRelative': 42.0, 'DoseGy': 36.0}
    
def test_parseDosimPar_4(strDosimPar='V 36$42 %'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Vxx%'] == {'VolumeRelative': 42.0, 'DoseGy': 36.0}

# Parse Vxxcc type dosimetric parameter
def test_parseDosimPar_5(strDosimPar='V60$3cc'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Vxxcc'] == {'VolumeAbsolute': 3.0, 'DoseGy': 60.0}

def test_parseDosimPar_6(strDosimPar='V 60$3cc'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Vxxcc'] == {'VolumeAbsolute': 3.0, 'DoseGy': 60.0}

def test_parseDosimPar_7(strDosimPar='V60$3 cc'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Vxxcc'] == {'VolumeAbsolute': 3.0, 'DoseGy': 60.0}

def test_parseDosimPar_8(strDosimPar='V 60$3 cc'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Vxxcc'] == {'VolumeAbsolute': 3.0, 'DoseGy': 60.0}
