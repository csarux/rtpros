import datetime
import io
import re
import pandas as pd
import xml.etree.ElementTree as ET
import pydicom as dcm
from textdistance import ratcliff_obershelp

def parseDose(strDose):
    '''
    Function: parseDose
        Parse the string specifying a dose and retrieve its numerical value in n Gy

    Arguments:
        srtDose: String
            The string specifying the dose in Gy

    Returns:
        Dose: Float
            The dose numerical value
    '''
    dose_rx_dict = {
        'Dose' : re.compile(r'(?P<Dose>(\d+)?\.?(\d+)?) Gy')
    }

    for key, rx in dose_rx_dict.items():
        match = rx.search(strDose)

    Dose = float(match.group('Dose'))
    return Dose

def parseDosimPar(strDosimPar):
    '''
    Function: parseDosimPar
        Parse the string specifying a a dosimetric parameter 

    Arguments:
        srtDosimPar: String
            The string specifying the dosimetric parameter

    Returns:
    '''
    dosimPar_rx_dict = {
        'Vxx%': re.compile(r'V(\s+)?(?P<Dose>\d+\.?(\d+)?)\$(?P<VolumeRelative>\d+\.?(\d+)?)(\s+)?\%$'),
        'Vxxcc': re.compile(r'V(\s+)?(?P<Dose>\d+\.?(\d+)?)\$(?P<VolumeAbsolute>\d+\.?(\d+)?)(\s+)?cc$'),
        'Dxx': re.compile(r'D(\s+)?(?P<Volume>\d+\.?(\d+)?)\$(?P<Dose>\d+\.?(\d+)?)(\s+)?\%?')
    }

    matches = {}
    for key, rx in dosimPar_rx_dict.items():
        match = rx.search(strDosimPar)
        if match:
            if key == 'Vxx%':
                VolumeRelative = float(match.group('VolumeRelative'))
                Dose = float(match.group('Dose'))
                matches[key] = {'VolumeRelative': VolumeRelative, 'DoseGy': Dose}
            if key == 'Vxxcc':
                VolumeAbsolute = float(match.group('VolumeAbsolute'))
                Dose = float(match.group('Dose'))
                matches[key] = {'VolumeAbsolute': VolumeAbsolute, 'DoseGy': Dose}
            if key == 'Dxx':
                Volume = float(match.group('Volume'))
                Dose = float(match.group('Dose'))
                matches[key] = {'VolumeRelative': Volume, 'Dose%': Dose}
        
    return matches        


'''
    Prescriptions
'''
def read_prescription(file):
    '''
    Function: read_prescription
    Arguments:
    file: Path file
    File containing the prescription. Exported from ARIA in csv format
    
    Returns:
    prdf: Pandas DataFrame
    Dataframe with the prescription data
    '''
    prdf = pd.read_csv(file)
    return prdf

def parse_prescription(file):
    '''
    Function: parse_prescription
    Arguments:
    file: Path file
    File containing the prescription. Exported from ARIA in csv format

    Returns: a tuple comtaining three dataframes pvdf, ccdf, oardf
    pvdf: Pandas DataFrame
    Dataframe with the prescription volumes
    ccdf: Pandas DataFrame
    Dataframe with the covarage constraints
    oardf: Pandas DataFrame
    Dataframe with oars restriction
    '''

    # Regular expession dictionary to filter the prescription volumes (PrescribedTo field)
    pv_rx_dict = {
        'Volume': re.compile(r'Volume (?P<Volume>.+)  \d+\.\d+ Gy '),
        'Dose': re.compile(r'  (?P<Dose>\d+\.\d+) Gy'),
        'FxDose' : re.compile(r'  (?P<FxDose>\d+\.\d+) Gy/Frac'),
    }

    # Regular expession dictionary to filter the CovarageConstraints
    cc_rx_dict = {
        'Volume': re.compile(r'Volume / Structure :(?P<Volume>.*) Min Dose'),
        'Min': re.compile(r'Min Dose:(?P<Min>.*) Gy Max'),
        'Max': re.compile(r'Max Dose:(?P<Max>.*) Gy At'),
        'AtLeast': re.compile(r'At Least (?P<AtLeast>.*) % of (?P<Volume>.*) at (?P<Percentage>.*) % (?P<Dose>.*) Gy No More Than'),
        'NoMore': re.compile(r'No More Than (?P<NoMore>.*) % of (?P<Volume>.*) at (?P<Percentage>.*) % (?P<Dose>.*) Gy'),
    }

    # Regular expession dictionary to filter the OAR constraints
    oar_rx_dict = {
        'Organ': re.compile(r'Organ :(?P<Organ>.*) Mean'),
        'Dmean': re.compile(r'Mean :(?P<Dmean>.*) Max Dose'),
        'Dmax' : re.compile(r'Max Dose :(?P<Dmax>.*)$'),
    }
   
    # Define parsing functions
    def _parse_prescription_volume(line):
        """
        Do a regex search against all defined regexes and
        return a dictionary the key and match result
    
        """
    
        matches = {}
        for key, rx in pv_rx_dict.items():
            match = rx.search(line)
            if match:
                matches[key] = match.group(key)
            
        return matches

    def _parse_volume(line):
        """
        Do a regex search against all defined CovarageConstraints regexes and
        return a dictionary the key and match result
    
        """
    
        matches = {}
        for key, rx in cc_rx_dict.items():
            match = rx.search(line)
            if match:
                if key == 'Volume':
                    volume = match.group(key)
                    matches[key] = match.group(key)
                elif key == 'AtLeast' and match.group('Volume') == volume:
                    constraint = [match.group('AtLeast'), match.group('Percentage'), match.group('Dose')]
                    matches[key] = constraint
                elif key == 'NoMore' and match.group('Volume') == volume:
                    constraint = [match.group('NoMore'), match.group('Percentage'), match.group('Dose')]
                    matches[key] = constraint
                else:
                    matches[key] = match.group(key)
            
        return matches
    
    def _parse_line(line):
        """
        Do a regex search against all defined OAR regexes and
        return the key and match result of the first matching regex
    
        """
    
        for key, rx in oar_rx_dict.items():
            match = rx.search(line)
            if match:
                return key, match
        # if there are no matches
        return None, None
        
    def _parse_organ(line):
        """
        Do a regex search against all defined OAR regexes and
        return a dictionary the key and match result
    
        """
    
        matches = {}
        for key, rx in oar_rx_dict.items():
            match = rx.search(line)
            if match:
                matches[key] = match.group(key).strip()
            
        return matches

    # Read the prescription file
    prdf = read_prescription(file)

    # Split the fields with the prescription volumes, covarage constraints and the organ at risk
    pv_lines = prdf.PrescribedTo.values[0].split('|')
    cc_lines = prdf.CoverageConstraints.values[0].split('|')
    oar_lines = prdf.OrgansAtRisk.values[0].split('\n')
    
    # Parse the prescription volume lines and create the pvdf dataframe
    pvdf = pd.DataFrame([_parse_prescription_volume(pv_line) for pv_line in pv_lines])
    
    # Parse the covarage constraint lines and create the ccdf dataframe
    ccdf = pd.DataFrame([_parse_volume(cc_line) for cc_line in cc_lines])

    # Parse the oar lines and create a list, each element with the lines corresponding a specific oar 
    oars, oar = [], None
    for oar_line in oar_lines:
        oar_key, oar_name = _parse_line(oar_line)
        if oar_key:
            oars.append(oar)
            oar = [oar_line]
        else:
            oar.append(oar_line.strip())
    oars.append(oar)
    oars.pop(0)
    oars
    # Parse each organ and create a list of dcitionaries with Dmin, Dmax and Dosimetric Parameters
    oars_list = []
    for oar in oars:
        oar_dict = _parse_organ(oar[0])
        oar_dict['DosimPars'] = oar[2:]
        oars_list.append(oar_dict)

    # Create the oardf dataframe
    oardf = pd.DataFrame(oars_list)

    return pvdf, ccdf, oardf

def getTreatmentDosePrescription(pvdf):
    '''
    Function: Retrieve the treatment dose prescription. 

    Arguments:
    pvdf: Pandas DataFrame
        Dataframe with the prescription volumes

    Returns:
    TreatmentDosePrescription: Float
        The PTV prescription with the highest dose 
    '''
    TreatmentDosePrescription = pvdf.Dose.astype('float').max()
    return TreatmentDosePrescription
    
'''
    Clinical protocols
'''
def parseProt(protin = 'BareBone.xml'):
    '''
    Function: Parse a clinical protocol

    Arguments:
    protin: String
        File name of the clinical protocal (XML formt)

    Returns:
    An ElementTree instance
    '''
    # Leer el protocolo clínico de entrada
    bbx = ET.parse(protin)
    return bbx

def modPreview(bbx, ID, ApprovalStatus='Unapproved', TreatmentSite='', AssignedUsers='salud\\50724293r'):
    '''
    Function: Modify the Preview section of a clinical protocol

    Arguments:
    bbx: An element tree instance
        The xml document to be modified
    ID: String
        The identification of the clinical protocol
    ApprovalStatus: String ('Unapproved' [Default], 'Approved', 'Reviewed', 'Retired')
        Clinical protocol approval status
    TreatmentSite:  String
        Clinical protocol treatment site
    AssignedUsers: String
        Aria User(s) writing the clinical protocol. It defaults to 'salud\50724293r'
    '''
    Preview = bbx.find('Preview')
    Preview.set('ID', ID)
    Preview.set('ApprovalStatus', ApprovalStatus)
    Preview.set('TreatmentSite', TreatmentSite)
    Preview.set('AssignedUsers', AssignedUsers)
    creationdatetime = datetime.datetime.strftime(datetime.datetime.now(), ' %B %d %Y %H:%M:%S:%f')[:-3]
    Preview.set('LastModified', creationdatetime)
    ApprovalHistory = AssignedUsers + ' Created [' + creationdatetime + ' ]'
    Preview.set('ApprovalHistory', ApprovalHistory)

def addStructure(bbx, structureName, stColourAndStyle='Countour - Brown', searchCT=1000, vDVHLineColor=-16777216):
    '''
    Function: Add a new structure to the Structures section of a clinical protocol

    Arguments:
    bbx: An element tree instance
        The xml document to be modified
    structureName: String
        The name of the structure to be added
    stColourAndStyle: String
        A string specifying the color and style of the structure. It defaults to 'Countour - Brown'
    searchCT: Int 
        An integer to set the SearchCTLow and SearchCTHigh fields
    vDVHLineColor:  Int
        A signed integer coding the DVH line color of the structure
    '''
    StructureTemplate = bbx.find('StructureTemplate')
    Structures = StructureTemplate.find('Structures')
    Structure = ET.SubElement(Structures, 'Structure')
    Structure.set('ID', structureName)
    Structure.set('Name', structureName)
    Identification = ET.SubElement(Structure, 'Identification')
    VolumeID = ET.SubElement(Identification, 'VolumeID')
    VolumeCode = ET.SubElement(Identification, 'VolumeCode')
    VolumeType = ET.SubElement(Identification, 'VolumeType')
    VolumeType.text = 'Organ'
    VolumeCodeTable = ET.SubElement(Identification, 'VolumeCodeTable')
    StructureCode = ET.SubElement(Identification, 'StructureCode')
    TypeIndex = ET.SubElement(Structure, 'TypeIndex')
    TypeIndex.text = str(2)
    ColorAndStyle = ET.SubElement(Structure, 'ColorAndStyle')
    ColorAndStyle.text = stColourAndStyle
    SearchCTLow = ET.SubElement(Structure, 'SearchCTLow')
    SearchCTLow.text = str(searchCT)
    SearchCTHigh = ET.SubElement(Structure, 'SearchCTHigh')
    SearchCTHigh.text = str(searchCT)
    DVHLineStyle = ET.SubElement(Structure, 'DVHLineStyle')
    DVHLineStyle.text = str(0)
    DVHLineColor = ET.SubElement(Structure, 'DVHLineColor')
    DVHLineColor.text = str(vDVHLineColor)
    DVHLineWidth = ET.SubElement(Structure, 'DVHLineWidth')
    DVHLineWidth.text = str(1)
    EUDAlpha = ET.SubElement(Structure, 'EUDAlpha')
    EUDAlpha.set('xsi:nil', 'true')
    TCPAlpha = ET.SubElement(Structure, 'TCPAlpha')
    TCPAlpha.set('xsi:nil', 'true')
    TCPBeta = ET.SubElement(Structure, 'TCPBeta')
    TCPBeta.set('xsi:nil', 'true')
    TCPGamma = ET.SubElement(Structure, 'TCPGamma')
    TCPGamma.set('xsi:nil', 'true')

def modPhase(bbx, ID, vFractionCount):
    '''
    Function: modify the Phase section

    Arguments:
    bbx: An element tree instance
    ID: String
        The Phase identification
    vFractionCount: Int
        The treatment fraction count
    '''
    Phases = bbx.find('Phases')
    Phase = Phases.find('Phase')
    Phase.set('ID', ID)
    FractionCount = Phase.find('FractionCount')
    FractionCount.text = str(vFractionCount)

def addPlanObjetive(bbx, ID, vParameter, vDose, vTotalDose, vPrimary='false', vModifier=1):
    '''
    Function: Add a Plan Objetive
    
    Arguments:
    bbx: An element tree instance
        The xml document to be modified
    ID: String
        Structure name which the plan objetive applies to
    VModifier: Int
        An index specifying the comparison operator to be used in Plan Objetive evaluation
             0: At Least (% receives more than)
             1: At Most (% receives more than). Default
             2: Minimum dose (is)
             3: Maximum dose (is)
             4: Mean dose (is)
             5: Reference point (receives)
             6: EUD (receives)
             7: Mean dose (is more than)
             8: Mean dose (is less than)
             9: Minimum dose (is more than)
            10: Maximum dose (is less than)
    vParameter: Float
        Volume percentage. Meaningless if vModifier is >= 2
    vDose: Float
        Fraction dose in Gy
    vTotalDose: Float
        Total dose in Gy
    '''
    Phases = bbx.find('Phases')
    Phase = Phases.find('Phase')
    Prescription = Phase.find('Prescription')
    Item = ET.SubElement(Prescription, 'Item')
    Item.set('ID', ID)
    Item.set('Primary', vPrimary)
    Type = ET.SubElement(Item, 'Type')
    Type.text = str(0) # hardcoded. It seems always default to zero
    Modifier = ET.SubElement(Item, 'Modifier')
    Modifier.text = str(vModifier)
    Parameter = ET.SubElement(Item, 'Parameter')
    Parameter.text = str(vParameter)
    Dose = ET.SubElement(Item, 'Dose')
    Dose.text = str(vDose)
    TotalDose = ET.SubElement(Item, 'TotalDose')
    TotalDose.text = str(vTotalDose)

def addQualityIndex(bbx, ID, vType, vModifier, vValue, vTypeSpecifier, vReportDQPValueInAbsoluteUnits):
    '''
    Function: Add a Quality Index
    
    Arguments:
    bbx: An element tree instance
        The xml document to be modified
    ID: String
        Structure name which the quality index applies to
    vType: Int
        An index specifying the Quality Index Type
            0: ConformityIndex
            1: GradientMeasure [cm]
            2: Vxx [%/cc of volume] where xx, dose percentage, is specified by vTypeSpecifier and the %/cc of volume by vValue
            3: Vxx Gy [%/cc of volume] where xx, absolute dose in Gy, is specified by vTypeSpecifier and the %/cc of volume by vValue
            4: Dxx [%/Gy] where xx, volume percentage, is specified by vTypeSpecifier and the %/Gy of volume by vValue
            5: Dxx cc [%/Gy] where xx, absolute volume in cc, is specified by vTypeSpecifier and the %/Gy of volume by vValue
    VModifier: Int
        An index specifying the comparison operator to be used in quality index evaluation
            0: is more than
            1: is less than
            2: is
    vValue: Float
        The constrain in %, Gy o cc
    vTypeSpecifier: Float
        The dose or volume in Vdose or Dvolume in %, Gy or cc
    vReportDQPValueInAbsoluteUnits: string {'true', 'false'}
        If the constrain is specified in absolute units
    '''
    Phases = bbx.find('Phases')
    Phase = Phases.find('Phase')
    Prescription = Phase.find('Prescription')
    MeasureItem = ET.SubElement(Prescription, 'MeasureItem')
    MeasureItem.set('ID', ID)
    Type = ET.SubElement(MeasureItem, 'Type')
    Type.text = str(vType)
    Modifier = ET.SubElement(MeasureItem, 'Modifier')
    Modifier.text = str(vModifier)
    Value = ET.SubElement(MeasureItem, 'Value')
    Value.text = str(vValue)
    TypeSpecifier = ET.SubElement(MeasureItem, 'TypeSpecifier')
    TypeSpecifier.text = str(vTypeSpecifier)
    ReportDQPValueInAbsoluteUnits = ET.SubElement(MeasureItem, 'ReportDQPValueInAbsoluteUnits')
    ReportDQPValueInAbsoluteUnits.text = vReportDQPValueInAbsoluteUnits

def writeProt(bbx, protout):
    '''
    Function: write a clinical protocol

    Arguments:
    bbx: An element tree instance
        The xml document to be written
    protout: String
        File name of the clinical protocal (XML formt) to be written
    '''
    ET.indent(bbx)
    bbx.write(protout, encoding='utf-8', xml_declaration=True)

def convertPrescriptionIntoClinicalProtocol(prescription, ProtocolID, TreatmentSite, PlanID, ProtTemplate='BareBone.xml', ProtOut='ClinicalProtocol.xml'):
    '''
    Function: Convert a prescription into a clinical protocol

    Arguments:
    prescription: String
        Prescription file name
    ProtocolID: String
        The identification of the clinical protocol in ARIA
    TreatmetSite: String
        The treatment anatomial region
    PlanID: String
        The plan identification
    ProtTemplate: String
        The xml document used as a clinical protocol template
    ProtOut: String
        Name of the xml file describing the clinical protocol
        
    '''
    # Read the prescriptiop
    pvdf, ccdf, oardf = parse_prescription(prescription)
    # Read protocol template
    bbx = parseProt(ProtTemplate)
    # Preview
    modPreview(bbx, ID=ProtocolID, TreatmentSite=TreatmentSite)
    # Phases
    FractionCount = int(float(pvdf.Dose[0])/float(pvdf.FxDose[0]))
    modPhase(bbx, ID=PlanID, vFractionCount=FractionCount)
    # Structutures
    for pv in pvdf.itertuples():
        addStructure(bbx, structureName=pv.Volume)
    for oar in oardf.itertuples():
        addStructure(bbx, structureName=oar.Organ)
    
    # Plan objetives
    for pv in pvdf.itertuples():
        ccVolumedf = ccdf[ccdf.Volume == pv.Volume]
        '''
        if not ccVolumedf.Min.str.match(' +')[0]:
            a=1
        if ccVolumedf.Max.str.match(' +')[0] == False:
            a=1
        '''
        if ccVolumedf.AtLeast.values[0]:
            atLeastlst = ccVolumedf.AtLeast.values[0]
            VolumePercentage =  atLeastlst[0]
            DosePercentage = float(atLeastlst[1])/100
            FxDoseGy = float(pv.FxDose) * DosePercentage
            DoseGy = float(pv.Dose) * DosePercentage
            addPlanObjetive(bbx, ID=pv.Volume, vParameter=VolumePercentage,
                                vDose=FxDoseGy, vTotalDose=DoseGy, vModifier=0)
        if ccVolumedf.NoMore.values[0]:
            noMorelst = ccVolumedf.NoMore.values[0]
            VolumePercentage =  noMorelst[0]
            DosePercentage = float(noMorelst[1])/100
            FxDoseGy = float(pv.FxDose) * DosePercentage
            DoseGy = float(pv.Dose) * DosePercentage
            addPlanObjetive(bbx, ID=pv.Volume, vParameter=VolumePercentage,
                                vDose=FxDoseGy, vTotalDose=DoseGy)
    for oar in oardf.itertuples():
        if oar.Dmean:
            ID = oar.Organ
            Parameter = 0
            Fxs = float(pvdf.Dose.values[0]) / float(pvdf.FxDose.values[0])
            TotalDose = parseDose(oar.Dmean)
            Dose = f'{TotalDose / Fxs:.5f}'
            addPlanObjetive(bbx, ID=ID, vParameter=Parameter, vDose=Dose, vTotalDose=TotalDose,
                                vModifier=8)
        if oar.Dmax:
            ID = oar.Organ
            Parameter = 0
            Fxs = float(pvdf.Dose.values[0]) / float(pvdf.FxDose.values[0])
            TotalDose = parseDose(oar.Dmax)
            Dose = f'{TotalDose / Fxs:.5f}'
            addPlanObjetive(bbx, ID=ID, vParameter=Parameter, vDose=Dose, vTotalDose=TotalDose,
                                vModifier=10)
        if oar.DosimPars:
            ID = oar.Organ
            for DosimPar in oar.DosimPars:
                constraint_dict = parseDosimPar(DosimPar)
                for key, constraint in constraint_dict.items():
                    if key == 'Vxx%':
                        VolumePercentage = constraint['VolumeRelative']
                        Fxs = float(pvdf.Dose.values[0]) / float(pvdf.FxDose.values[0])
                        TotalDose = constraint['DoseGy']
                        Dose = f'{TotalDose / Fxs:.5f}'
                        addPlanObjetive(bbx, ID=ID, vParameter=VolumePercentage, vDose=Dose, vTotalDose=TotalDose,
                                            vModifier=1)
                        
    # Quality Indexes
    for pv in pvdf.itertuples():
        ccVolumedf = ccdf[ccdf.Volume == pv.Volume]
        if ccVolumedf.AtLeast.values[0]:
            TreatmentDosePrescription = getTreatmentDosePrescription(pvdf)
            atLeastlst = ccVolumedf.AtLeast.values[0]
            VolumePercentage =  atLeastlst[0]
            DosePercentage = float(atLeastlst[1])/100
            StructureRelativeDose = float(pv.Dose) * DosePercentage / TreatmentDosePrescription * 100
            addQualityIndex(bbx, ID=pv.Volume, vType=2, vModifier=0, 
                                vValue=VolumePercentage, vTypeSpecifier=StructureRelativeDose, 
                                vReportDQPValueInAbsoluteUnits='false')
        if ccVolumedf.NoMore.values[0]:
            TreatmentDosePrescription = getTreatmentDosePrescription(pvdf)
            noMorelst = ccVolumedf.NoMore.values[0]
            VolumePercentage = noMorelst[0]
            DosePercentage = float(noMorelst[1])/100
            StructureRelativeDose = float(pv.Dose) * DosePercentage / TreatmentDosePrescription * 100
            addQualityIndex(bbx, ID=pv.Volume, vType=2, vModifier=1, 
                                vValue=VolumePercentage, vTypeSpecifier=StructureRelativeDose, 
                                vReportDQPValueInAbsoluteUnits='false')
    
    for oar in oardf.itertuples():
        if oar.DosimPars:
            ID = oar.Organ
            for DosimPar in oar.DosimPars:
                constraint_dict = parseDosimPar(DosimPar)
                for key, constraint in constraint_dict.items():
                    if key == 'Vxx%':
                        VolumePercentage = constraint['VolumeRelative']
                        PrescriptionDoseGy = pvdf.Dose.astype('float').max()
                        ConstraintDoseGy = constraint['DoseGy']
                        StructureRelativeDose = f'{ConstraintDoseGy / PrescriptionDoseGy * 100:.5f}'
                        addQualityIndex(bbx, ID=ID, vType=2, vModifier=1, 
                                            vValue=VolumePercentage, vTypeSpecifier=StructureRelativeDose, 
                                            vReportDQPValueInAbsoluteUnits='false')
                    if key == 'Vxxcc':
                        VolumeAbsolute = constraint['VolumeAbsolute']*1000
                        PrescriptionDoseGy = pvdf.Dose.astype('float').max()
                        ConstraintDoseGy = constraint['DoseGy']
                        StructureRelativeDose = f'{ConstraintDoseGy / PrescriptionDoseGy * 100:.5f}'
                        addQualityIndex(bbx, ID=ID, vType=2, vModifier=1, 
                                            vValue=VolumeAbsolute, vTypeSpecifier=StructureRelativeDose, 
                                            vReportDQPValueInAbsoluteUnits='true')
                    if key == 'Dxx':
                        VolumePercentage = constraint['VolumeRelative']
                        StructureRelativeDose = constraint['Dose%']
                        addQualityIndex(bbx, ID=ID, vType=4, vModifier=1, 
                                            vValue=VolumePercentage, vTypeSpecifier=StructureRelativeDose, 
                                            vReportDQPValueInAbsoluteUnits='false')
    
    # Write clincial protocol
    writeProt(bbx, ProtOut)

'''
    Contouring
'''

def readContouringStructureNames(rsdicom):
    '''
    Function: Read RT Dicom structure set file and generate a list of structure names

    Arguments:
    rsdicom: String
        File Path to the RT Dicom structure set

    Return:
        constrnames: list
        A list of the structure names given in ARIA
    '''
    dcmds = dcm.read_file(rsdicom)
    strsetsq = dcmds.StructureSetROISequence
    contstrnames = [structure.ROIName for structure in strsetsq]
    return contstrnames

def readClinProtStructureNames(clinprot):
    '''
    Function: Read the structure names in the clinical protocol xml file

    Arguments:
    clinprot: String
        File Path to the clinical protocol xml file

    Return:
        protstrnames: list
        A list of the structure names given in the clinical protocol xml file
    '''
    tree = ET.parse(clinprot)
    root = tree.getroot()
    structures = root.find('StructureTemplate').find('Structures')
    protstrnames = [structure.get('ID') for structure in structures.findall('Structure')]
    return protstrnames

def checkStructureNameLength(strnames):
    '''
    Function: Check if the structure name length is less than 16 characters

    Arguments:
    strnames: List
        Structure name list

    Return:
        invalidStrNames: List
        List of contouring structures names with length greater than 16 characters
    '''
    invalidStrNames = []
    for strname in strnames:
        if len(strname) > 16:
            invalidStrNames.append(strname)
    return invalidStrNames

def _suggestStrNames(strlistA, strlistB):
    '''
    Function: Suggest changes in a list of structure names based on the names of the other list 

    Arguments:
    strlistA: List
        Structure name list to be corrected

    strlistB: List
        Structure name list taken as reference

    Return:
        suggestiondf: Pandas DataFrame
        A pandas DataFrame which index is the names of the structures to be corrected and its column is the structure name suggested
    '''
    infstrdf = pd.DataFrame([{strB: ratcliff_obershelp(strA, strB) 
                              for strB in strlistB} 
                                for strA in strlistA], index=strlistA)
    infstrdf['Suggestion'] = infstrdf.idxmax(axis=1)
    suggestiondf = pd.DataFrame(infstrdf['Suggestion'])
    suggestiondf.reset_index(names='Structure', inplace=True)
    return suggestiondf

def suggestStrNames(clinprot, rsdicom):
    '''
    Function: Suggest changes in a list of structure names based on the names of the other list 

    Arguments:
    clinprot: String
        File Path to the clinical protocol xml file containing the structure names to be corrected

    rsdicom: String
        File Path to the RT Dicom containing the reference structure set

    Return:
        suggestiondf: Pandas DataFrame
        A pandas DataFrame which index is the names of the structures to be corrected and its column is the structure name suggested
    '''

    protstrnames = readClinProtStructureNames(clinprot)
    contstrnames = readContouringStructureNames(rsdicom)
    invalidStrNames = checkStructureNameLength(contstrnames)
    sep = ', '
    if invalidStrNames:
        raise NameError('''
        The following structures are more than 16 characters long
        which is not allowed for the clinical protocol definition.\n
        ''' + sep.join(invalidStrNames))
    invalidStrNames = checkStructureNameLength(protstrnames)
    if invalidStrNames:
        raise NameError('''
        The following structures are more than 16 characters long
        which is not allowed for the clinical protocol definition
        ''' + sep.join(invalidStrNames))
    suggestiondf = _suggestStrNames(protstrnames, contstrnames)
    return suggestiondf

def _correctStrNames(filedata, strNameChanges):
    '''
    Function: Correct structure names in a prescrption file following a DataFrame of directions  

    Arguments:
    filedata: String
        The text content of a prescription csv file to be corrected

    strNameChanges: DataFrame
        Pandas datafrmae with the old and new names of each structure to be corrected

    Return:
        filedata: String
        The corrected text of the prescription csv file
    '''
    for index, strName in strNameChanges.iterrows():
        filedata = filedata.replace(strName.Old, strName.New)
    return filedata

def correctStrNames(prescriptionFile, strNameChanges):
    '''
    Function: Correct structure names in a prescrption file following a DataFrame of directions  

    Arguments:
    prescriptionFile: String
        The path to the prescription csv file to be corrected

    strNameChanges: DataFrame
        Pandas datafrmae with the old and new names of each structure to be corrected

    '''
    # Read the prescription file
    with open(prescriptionFile, 'r') as file:
      filedata = file.read()
    # Correct the prescription file
    filedata = _correctStrNames(filedata, strNameChanges)
    # Write the corrected prescription file
    with open(prescriptionFile, 'w') as file:
      file.write(filedata)
