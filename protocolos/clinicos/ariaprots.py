import pandas as pd
import io
import re

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
    prdf = pd.read_csv('prescripciones/orl_radical.csv')
    return prdf

def parse_prescription(file):
    '''
    Function: parse_prescription
    Arguments:
    file: Path file
    File containing the prescription. Exported from ARIA in csv format

    Returns: a tuple comtaining two dataframes ccdf, oardf
    ccdf: Pandas DataFrame
    Dataframe with the covarage constraints
    oardf: Pandas DataFrame
    Dataframe with oars restriction
    '''

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
                matches[key] = match.group(key)
            
        return matches

    # Read the prescription file
    prdf = read_prescription(file)

    # Split the fields with the covarage constraints and the organ at risk
    cc_lines = prdf.CoverageConstraints.values[0].split('|')
    oar_lines = prdf.OrgansAtRisk.values[0].split('\n')
    
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
            oar.append(oar_line)
    oars.remove(None)

    # Parse each organ and create a list of dcitionaries with Dmin, Dmax and Dosimetric Parameters
    oars_list = []
    for oar in oars:
        oar_dict = _parse_organ(oar[0])
        oar_dict['DosimPars'] = oar[2:]
        oars_list.append(oar_dict)

    # Create the oardf dataframe
    oardf = pd.DataFrame(oars_list)

    return ccdf, oardf

