# Copyright (c) 2004-2006, Nathan R. Yergler, Creative Commons
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
rest-wx-client.py
$Id$

Sample implementation of REST client using wxPython.
(c) 2004-2005, Nathan R. Yergler, Creative Commons

"""

import urllib2
import lxml.etree
from StringIO import StringIO

import wx
import wx.lib.dialogs

class CcRest:
    """Wrapper class to decompose REST XML responses into Python objects."""
    
    def __init__(self, root):
        self.root = root

        self.__lc_doc = None

    def locales(self):
        """Return a sequence of valid locales for the web services."""

        # retrieve the locales XML document
        url = '%s/%s' % (self.root, 'locales')
        locale_xml = urllib2.urlopen(url).read()

        # parse the document and extract the list of locale ids
        doc = lxml.etree.parse(StringIO(locale_xml))
        locales = doc.xpath('//locale/@id')

        return [n for n in locales]

    def license_classes(self, lang='en'):
        """Returns a dictionary whose keys are license IDs, with the
        license label as the value."""

        lc_url = '%s/%s' % (self.root, 'classes')

        # retrieve the licenses document and store it
        self.__lc_doc = urllib2.urlopen(lc_url).read()

        # parse the document and return a dictionary
        lc = {}
        d = lxml.etree.parse(StringIO(self.__lc_doc))

        licenses = d.xpath('//licenses/license')

        for l in licenses:
            lc[l.attrib['id']] = l.text
            
        return lc
        
    def fields(self, license, lang='en'):
        """Retrieves details for a particular license."""

        l_url = '%s/license/%s' % (self.root, license)

        # retrieve the license source document
        self.__l_doc = urllib2.urlopen(l_url).read()

        print self.__l_doc
        
        d = lxml.etree.parse(StringIO(self.__l_doc))
        
        self._cur_license = {}

        fields = d.xpath('//field')

        for field in fields:
            f_id = field.attrib['id']
            self._cur_license[f_id] = {}

            self._cur_license[f_id]['label'] = \
                              field.xpath('label')[0].text
            if len(field.xpath('description')) > 0:
                self._cur_license[f_id]['description'] = \
                                  field.xpath('description')[0].text
            else:
                self._cur_license[f_id]['description'] = ''
                
            self._cur_license[f_id]['type'] = \
                              field.xpath('type')[0].text
            self._cur_license[f_id]['enum'] = {}

            # extract the enumerations
            enums = field.xpath('enum')
            for e in enums:
                e_id = e.attrib['id']
                try:
                    self._cur_license[f_id]['enum'][e_id] = \
                         e.xpath('label')[0].text
                except IndexError, e:
                    self._cur_license[f_id]['enum'][e_id] = e_id
            
        return self._cur_license

    def issue(self, license, answers, lang='en'):
        l_url = '%s/license/%s/issue' % (self.root, license)

        # construct the answers.xml document from the answers dictionary
        answer_xml = """
        <answers>
          <locale>%s</locale>
          <license-%s>""" % (lang, license)

        for key in answers:
            answer_xml = """%s
            <%s>%s</%s>""" % (answer_xml, key, answers[key], key)

        answer_xml = """%s
          </license-%s>
        </answers>
        """ % (answer_xml, license)

        
        # retrieve the license source document
        self.__a_doc = urllib2.urlopen(l_url,
                                       data='answers=%s' % answer_xml).read()

        return self.__a_doc
        
class LicenseFrame(wx.Frame):
    REST_ROOT = 'http://localhost:8080' # api.creativecommons.org/rest/dev'
    
    def __init__(self, parent, title=None):
        wx.Frame.__init__(self, None, title=title)

        # initialize tracking attributes
        self.__license = ''
        self.__fields = []
        self.__fieldinfo = {}

        # create the web services proxy
        self.__cc_server = CcRest(self.REST_ROOT)
        
        # create the primary frame sizer
        self.sizer = wx.GridBagSizer(5, 5)
        self.sizer.AddGrowableCol(0)
        self.sizer.AddGrowableRow(2)
        self.SetSizer(self.sizer)

        # create the basic widgets
        self.cmbLicenses = wx.ComboBox(self,
                                       style=wx.CB_DROPDOWN|wx.CB_READONLY
                                       )
        self.sizer.Add(self.cmbLicenses, (1,0),
                       flag=wx.EXPAND|wx.ALL)

        self.cmbLocales = wx.ComboBox(self,
                                      style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self.sizer.Add(self.cmbLocales, (0,0), flag=wx.EXPAND|wx.ALL)

        # set up a call later to update the license class list
        wx.CallAfter(self.getLicenseClasses)

        # create the panel for the fields
        self.pnlFields = wx.Panel(self)
        self.sizer.Add(self.pnlFields, (2,0),
                       flag=wx.EXPAND|wx.ALL)

        self.cmdLicense = wx.Button(self, label="Get License")
        self.sizer.Add(self.cmdLicense, (3,0), flag = wx.ALIGN_RIGHT)

        # set up the field panel sizer
        self.fieldSizer = wx.FlexGridSizer(0, 2, 5, 5)
        self.fieldSizer.AddGrowableCol(1)
        self.pnlFields.SetSizer(self.fieldSizer)

        # bind event handlers
        self.Bind(wx.EVT_COMBOBOX, self.onSelectLicenseClass, self.cmbLicenses)
        self.Bind(wx.EVT_BUTTON,   self.onLicense,       self.cmdLicense)

    def getLicenseClasses(self):
        """Calls the SOAP API via proxy to get a list of all available
        license class identifiers."""

        # update the list of license classes
        self.__l_classes = self.__cc_server.license_classes()
        self.cmbLicenses.AppendItems(self.__l_classes.values())
        self.cmbLicenses.SetValue('')

        # update the list of locales
        locales = self.__cc_server.locales()
        self.cmbLocales.AppendItems(locales)
        self.cmbLocales.SetValue('en')

    def onLicense(self, event):
        """Submit selections and display license info."""
        answers = {}

        for field in self.__fields:
            if self.__fieldinfo[field]['type'] == 'enum':
                answer_key = [n for n in self.__fieldinfo[field]['enum'].keys() if
                              self.__fieldinfo[field]['enum'][n] ==
                              self.__fieldinfo[field]['control'].GetValue()][0]

                answers[field] = answer_key 

        wx.lib.dialogs.alertDialog(self,
                       self.__cc_server.issue(self.__license, answers,
                                              self.cmbLocales.GetValue()),
                       'License Results')
        
    def onSelectLicenseClass(self, event):
        if event.GetString() == '' or event.GetString() == self.__license:
            # bail out if there's no change; we'll get called again momentarily
            return
        
        # get the new license ID
        self.__license = [n for n in self.__l_classes.keys()
                          if self.__l_classes[n] == event.GetString()][0]
        
        # clear the sizer
        self.pnlFields.GetSizer().Clear(True)

        # retrieve the fields
        fields = self.__cc_server.fields(self.__license)
        self.__fields = fields.keys()
        self.__fieldinfo = fields

        for field in self.__fields:
            # update the UI
            self.updateFieldDetails(field)

    def updateFieldDetails(self, fieldid):
        
        field = fieldid
        self.__fieldinfo[field] = dict(self.__fieldinfo[field])

        # make sure we have a label
        if self.__fieldinfo[field]['label'] == '':
            self.__fieldinfo[field]['label'] = field

        # add the label text
        self.__fieldinfo[field]['label_ctrl'] = wx.StaticText(
            self.pnlFields,
            label=self.__fieldinfo[field]['label'])

        self.pnlFields.GetSizer().Add(self.__fieldinfo[field]['label_ctrl'])
        # add the control
        if self.__fieldinfo[field]['type'] == 'enum':
            # enumeration field; retrieve the possibilities
            self.__fieldinfo[field]['control'] = \
                 wx.ComboBox(self.pnlFields,
                             style=wx.CB_DROPDOWN|wx.CB_READONLY,
                             choices = self.__fieldinfo[field]['enum'].values()
                             )
            self.__fieldinfo[field]['control'].SetSelection(0)
            self.pnlFields.GetSizer().Add(
                self.__fieldinfo[field]['control'],
                flag = wx.EXPAND | wx.ALL)

        # add tooltip help
        wx.HelpProvider.Get().AddHelp(self.__fieldinfo[field]['control'],
                                      self.__fieldinfo[field]['description'])
        wx.HelpProvider.Get().AddHelp(self.__fieldinfo[field]['label_ctrl'],
                                      self.__fieldinfo[field]['description'])

                    
        self.Fit()
        
if __name__ == '__main__':
    app = wx.PySimpleApp()
    wx.HelpProvider.Set(wx.SimpleHelpProvider())
    main = LicenseFrame(None, title="Chooser")
    main.Show()
    app.MainLoop()
