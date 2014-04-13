#!/usr/bin/env python

def decision(audiocorr, audiofreq, 
             wifijacc, wifiabs, wifieucl, wifiexp, wifisumsqua, 
             bluejacc, blueabs,
             gpsjaccwhole, gpsabs, gpseucl, gpsexp, gpssubset):
    """ Make decision upon offline model
        @param: 14 features (although gpsabs and gpsexp are not used)
        @return: True/False --> Copresence/Non-copresence
    """
    
    if audiocorr <= 0.11715:
        if wifiexp <= 1.80173474238E23:
            if wifiexp <= 1.74325390567E23:
                if wifisumsqua <= 148:
                    if wifiabs <= 15.928:
                        if wifisumsqua <= 52:
                            if wifijacc <= 0.786:
                                if wifiabs <= 8.152:
                                    return True
                                else:
                                    if gpseucl <= 43.312:
                                        if gpsjaccwhole <= 0.25:
                                            if audiocorr <= 0.044762:
                                                return False
                                            else:
                                                return True
                                        else:
                                            if bluejacc <= 0.5:
                                                if wifisumsqua <= 18:
                                                    return True
                                                else:
                                                    return False
                                            else:
                                                return True
                                    else:
                                        if wifisumsqua <= 6:
                                            if blueabs <= 55:
                                                if wifijacc <= 0.681:
                                                    return False
                                                else:
                                                    return True
                                            else:
                                                if wifieucl <= 60.756:
                                                    return False
                                                else:
                                                    if wifiabs <= 15.6:
                                                        return True
                                                    else:
                                                        return False
                                        else:
                                            if audiocorr <= 0.041289:
                                                if audiofreq <= 1.4771:
                                                    if bluejacc <= 0.571:
                                                        return False
                                                    else:
                                                        if audiofreq <= 1.3683:
                                                            return True
                                                        else:
                                                            return False
                                                else:
                                                    return True
                                            else:
                                                return True
                            else:
                                return True
                        else:
                            return True
                    else:
                        if audiofreq <= 1.3666:
                            if gpsexp <= 4.29289457197E13:
                                return True
                            else:
                                if audiocorr <= 0.026771:
                                    return True
                                else:
                                    if audiocorr <= 0.026951:
                                        return False
                                    else:
                                        return True
                        else:
                            if gpsjaccwhole <= 0.667:
                                if audiocorr <= 0.009068:
                                    return True
                                else:
                                    return False
                            else:
                                return True
                else:
                    if wifiexp <= 2435975082.13:
                        return True
                    else:
                        if audiocorr <= 0.050743:
                            if wifiabs <= 15.444:
                                if wifijacc <= 0.383:
                                    return False
                                else:
                                    if wifiabs <= 13.062:
                                        return True
                                    else:
                                        return False
                            else:
                                return False
                        else:
                            if wifijacc <= 0.667:
                                return True
                            else:
                                if gpssubset <= 0.333:
                                    if audiofreq <= 1.4533:
                                        return False
                                    else:
                                        return True
                                else:
                                    return False
            else:
                if audiocorr <= 0.011791:
                    return True
                else:
                    return False
        else:
            return False
    else:
        if wifisumsqua <= 508:
            if wifieucl <= 17.613:
                if wifiexp <= 2222113.05:
                    return True
                else:
                    return False
            else:
                return True
        else:
            if wifijacc <= 0.667:
                return True
            else:
                return False
    