import aclinprot as acp

Vxx_test = 'data/Vxx.csv'

def test_parse_prescription(prescription_test = Vxx_test):
    acp.parse_prescription(prescription_test)

# Parse Vxx% type dosimetric parameter
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

# Parse Dxxcc_Gy type dosimetric parameter
def test_parseDosimPar_9(strDosimPar='D950cc$7.2Gy'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Dxxcc_Gy'] == {'VolumeAbsolute': 950, 'DoseGy': 7.2}
def test_parseDosimPar_10(strDosimPar='D950 cc$7.2 Gy'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Dxxcc_Gy'] == {'VolumeAbsolute': 950, 'DoseGy': 7.2}
def test_parseDosimPar_11(strDosimPar='D 950 cc$7.2 Gy'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Dxxcc_Gy'] == {'VolumeAbsolute': 950, 'DoseGy': 7.2}
def test_parseDosimPar_12(strDosimPar='D 950 cc$7.2 Gy'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Dxxcc_Gy'] == {'VolumeAbsolute': 950, 'DoseGy': 7.2}

# Parse Dxx_Gy type dosimetric parameter
def test_parseDosimPar_13(strDosimPar='D 1500$12.5 Gy'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Dxx_Gy'] == {'VolumeAbsolute': 1500, 'DoseGy': 12.5}
def test_parseDosimPar_14(strDosimPar='D1500$12.5Gy'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Dxx_Gy'] == {'VolumeAbsolute': 1500, 'DoseGy': 12.5}
def test_parseDosimPar_15(strDosimPar='D 1500$12.5  Gy'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Dxx_Gy'] == {'VolumeAbsolute': 1500, 'DoseGy': 12.5}
def test_parseDosimPar_16(strDosimPar='D1500$12.5 Gy'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Dxx_Gy'] == {'VolumeAbsolute': 1500, 'DoseGy': 12.5}

# Parse Dxx%_Gy type dosimetric parameter
def test_parseDosimPar_17(strDosimPar='D40%$7.3Gy'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Dxx%_Gy'] == {'VolumeRelative': 40, 'DoseGy': 7.3}
def test_parseDosimPar_18(strDosimPar='D40%$7.3 Gy'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Dxx%_Gy'] == {'VolumeRelative': 40, 'DoseGy': 7.3}

# Parse Vxx% type dosimetric parameter with Dose in Gy
def test_parseDosimPar_19(strDosimPar='V35Gy$67%'):
    actual = acp.parseDosimPar(strDosimPar)
    assert actual['Vxx%'] == {'VolumeRelative': 67.0, 'DoseGy': 35.0}
    

