import xml.etree.ElementTree as etree
from datetime import datetime
from urllib2 import Request, urlopen, URLError
import csv
import sys
import re

# SPALSH
print '''  

    -------------------------------------------------
     _     ____  ____       _   _   _ ____ ___ _____ 
    | |   |  _ \/ ___|     / \ | | | |  _ \_ _|_   _|
    | |   | | | \___ \    / _ \| | | | | | | |  | |  
    | |___| |_| |___) |  / ___ \ |_| | |_| | |  | |  
    |_____|____/|____/  /_/   \_\___/|____/___| |_|  
    
    This utility performs the NZGOAL LDS audit by
    comparing the LDS RSS feed with the NZGOAL
    google form questionnaire as exported in tsv.
    For more information. Please see the geodetic wiki 
    -------------------------------------------------
                                                  
     '''

# RESULT CATEGORIES
result = {'pub' : {}, #publish
       'pwr' : {}, #publish with restrictions
       'dnp' : {}, #do not publish
       'nid' : {}, #no id - id not in tsv
}

mappings_for_humans = {'nid' : 'No Corresponding lds id In Forms Spread Sheet (.tsv):',
                       'pwr' : 'Publish With Restrictions:',
                       'pub' : 'Publish:',
                       'dnp' : 'Do Not Publish:'
                       }
                       
                             
# GET USER INPUTS
#date_from = '11/01/16'
date_from = raw_input("Audit Date From (dd/mm/yy): ")
date_from = datetime.strptime(date_from, "%d/%m/%y").date()
#date_to = '11/07/16'
date_to = raw_input("Audit Date To (dd/mm/yy):")
date_to = datetime.strptime(date_to, "%d/%m/%y").date()
#tsv_file = '~/NZ Goal Data Test - Form Responses 1.tsv'
tsv_file = raw_input("csv file path: ") 

# PROCESS FORMS SPREADSHEET

# Read in tsv
with open(tsv_file, 'rb') as tsv:
    reader = csv.reader(tsv, delimiter='\t')
    header = reader.next()
    num_cols = len(header)
    
    # Check an id column was added to tsv as per instructions

    if header[0].upper() != 'ID':
        print 'EXITING - The first column has not be titled "id" as per the instructions'
        sys.exit()
        
    # COMPILE FORM DATA (DICTIONARY)
    form_data = {}
    for row in reader:
        id = row[0]
        
        # last question answered
        pos_last_q =  [i for i,x in enumerate(row) if x !=''][-1]
        str_last_q = header[pos_last_q]
        
        # Categorise based on last answer
        if re.match( r'.*RELEASE\.$', str_last_q):
            form_data[id]='pub' #publish
        elif re.match( r'(^Do not publish.*)', str_last_q):
            form_data[id]='dnp' #do not publish
        elif re.match( r'(.*release to restricted audience.*)', str_last_q):
            form_data[id]='pwr'  #publish with restrictions
        else:
            print '''SCRIPT FAILED WHEN MATCHING TSV HEADER TEXT WITH CODE FOR 
                    FOR CATEGORISATION. \n Has the forms outcomes wording changed?'''

            sys.exit()
    
    # COMAPRE LDS RSS DATA TO FORM DATA
    print '\nAssessing RSS Data:'
    
    for data_type in ('tables', 'layers'):
        status = 200
        page = 1
        feed = '{http://www.w3.org/2005/Atom}'
        while status == 200:
            if page % 2 == 0:
                print '|',
                
            req = Request('http://data.linz.govt.nz/feeds/layers?page={}'.format(page))
            try:
                response = urlopen(req)
                status = response.getcode()
                data = response.read()
                tree = etree.fromstring(data)
                entries = tree.findall(feed+'entry') 
                    
                for e in entries:
                    data_set_date = e.find(feed+'published').text.rsplit('T')[0]
                    data_set_date = datetime.strptime(data_set_date, "%Y-%m-%d").date()
                    
                    # Only consider data between user input dates
                    if data_set_date >= date_from and data_set_date <= date_to:
                        rss_id = e.find(feed+'id').text #<id>tag:data.linz.govt.nz,2016-09:layers:3452</id>
                        re_match = re.match( r'(.*layers:)([0-9]{1,5}).*', rss_id, re.I)
                        rss_id = re_match.group(2)
                                                
                        #find id in form_data
                        form_record = form_data.get(rss_id, None)
                        if form_record:
                            result[form_record].update({rss_id: {'name' : e.find(feed+'title').text, 'date_pub':e.find(feed+'published').text}})       
                        else :
                            result['nid'].update({rss_id: {'name' : e.find(feed+'title').text, 'date_pub':e.find(feed+'published').text}})       
   
            except URLError, e:
                status = e.getcode()
            response.close()
            page += 1


# PRINT THE RESULTS
print '''
\n>>>RESULTS:\nThe script has found all LDS ids of those public datasets 
published between the provided dates.The results are categorised based
on the outcomes of the forms questionnaire, except those that did not find 
a matching id in the tsv/ spreadsheet. These are out-putted here under 
the section "NO CORRESPONDING LDS ID IN FORMS SPREAD SHEET (.TSV)"
'''
            
for k, v in result.items():
    print '{0}{1}{2}{1}'.format('-'*100,'\n', mappings_for_humans.get(k).upper())
    print '{0}{1}{2}'.format('lds_id:', '\tDate Pub:', '\t'*2+'Data Set Name:')
    for id, data in v.items():
        print '{0}:\t{2}\t{1}'.format(id, data['name'], data['date_pub'] )
  
