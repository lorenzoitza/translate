# -*- coding: utf-8 -*-

from pytest import mark

from translate.convert import prop2po, test_convert
from translate.misc import wStringIO
from translate.storage import po, properties


class TestProp2PO:

    def prop2po(self, propsource, proptemplate=None, personality="java"):
        """helper that converts .properties source to po source without requiring files"""
        inputfile = wStringIO.StringIO(propsource)
        inputprop = properties.propfile(inputfile, personality=personality)
        convertor = prop2po.prop2po(personality=personality)
        if proptemplate:
            templatefile = wStringIO.StringIO(proptemplate)
            templateprop = properties.propfile(templatefile)
            outputpo = convertor.mergestore(templateprop, inputprop)
        else:
            outputpo = convertor.convertstore(inputprop)
        return outputpo

    def convertprop(self, propsource):
        """call the convertprop, return the outputfile"""
        inputfile = wStringIO.StringIO(propsource)
        outputfile = wStringIO.StringIO()
        templatefile = None
        assert prop2po.convertprop(inputfile, outputfile, templatefile)
        return outputfile.getvalue()

    def singleelement(self, pofile):
        """checks that the pofile contains a single non-header element, and returns it"""
        assert len(pofile.units) == 2
        assert pofile.units[0].isheader()
        print(pofile)
        return pofile.units[1]

    def countelements(self, pofile):
        """counts the number of non-header entries"""
        assert pofile.units[0].isheader()
        print(pofile)
        return len(pofile.units) - 1

    def test_simpleentry(self):
        """checks that a simple properties entry converts properly to a po entry"""
        propsource = 'SAVEENTRY=Save file\n'
        pofile = self.prop2po(propsource)
        pounit = self.singleelement(pofile)
        assert pounit.source == "Save file"
        assert pounit.target == ""

    def test_convertprop(self):
        """checks that the convertprop function is working"""
        propsource = 'SAVEENTRY=Save file\n'
        posource = self.convertprop(propsource)
        pofile = po.pofile(wStringIO.StringIO(posource))
        pounit = self.singleelement(pofile)
        assert pounit.source == "Save file"
        assert pounit.target == ""

    def test_tab_at_end_of_string(self):
        """check that we preserve tabs at the end of a string"""
        propsource = r"TAB_AT_END=This setence has a tab at the end.\t"
        pofile = self.prop2po(propsource)
        pounit = self.singleelement(pofile)
        assert pounit.source == "This setence has a tab at the end.\t"

        propsource = r"SPACE_THEN_TAB_AT_END=This setence has a space then tab at the end. \t"
        pofile = self.prop2po(propsource)
        pounit = self.singleelement(pofile)
        assert pounit.source == "This setence has a space then tab at the end. \t"

        propsource = r"SPACE_AT_END=This setence will keep its 4 spaces at the end.    "
        pofile = self.prop2po(propsource)
        pounit = self.singleelement(pofile)
        assert pounit.source == "This setence will keep its 4 spaces at the end.    "

        propsource = r"SPACE_AT_END_NO_TRIM=This setence will keep its 4 spaces at the end.\    "
        pofile = self.prop2po(propsource)
        pounit = self.singleelement(pofile)
        assert pounit.source == "This setence will keep its 4 spaces at the end.    "

        propsource = r"SPACE_AT_END_NO_TRIM2=This setence will keep its 4 spaces at the end.\\    "
        pofile = self.prop2po(propsource)
        pounit = self.singleelement(pofile)
        assert pounit.source == "This setence will keep its 4 spaces at the end.\    "

    def test_tab_at_start_of_value(self):
        """check that tabs in a property are ignored where appropriate"""
        propsource = r"property	=	value"
        pofile = self.prop2po(propsource)
        pounit = self.singleelement(pofile)
        assert pounit.getlocations()[0] == "property"
        assert pounit.source == "value"

    def test_unicode(self):
        """checks that unicode entries convert properly"""
        unistring = r'Norsk bokm\u00E5l'
        propsource = 'nb = %s\n' % unistring
        pofile = self.prop2po(propsource)
        pounit = self.singleelement(pofile)
        print(repr(pofile.units[0].target))
        print(repr(pounit.source))
        assert pounit.source == u'Norsk bokm\u00E5l'

    def test_multiline_escaping(self):
        """checks that multiline enties can be parsed"""
        propsource = r"""5093=Unable to connect to your IMAP server. You may have exceeded the maximum number \
of connections to this server. If so, use the Advanced IMAP Server Settings dialog to \
reduce the number of cached connections."""
        pofile = self.prop2po(propsource)
        print(repr(pofile.units[1].target))
        assert self.countelements(pofile) == 1

    def test_comments(self):
        """test to ensure that we take comments from .properties and place them in .po"""
        propsource = '''# Comment
prefPanel-smime=Security'''
        pofile = self.prop2po(propsource)
        pounit = self.singleelement(pofile)
        assert pounit.getnotes("developer") == "# Comment"

    def test_multiline_comments(self):
        """test to ensure that we handle multiline comments well"""
        propsource = '''# Comment
# commenty 2

## @name GENERIC_ERROR
## @loc none
prefPanel-smime=
'''
        pofile = self.prop2po(propsource)
        print(bytes(pofile))
        #header comments:
        assert b"#. # Comment\n#. # commenty 2" in bytes(pofile)
        pounit = self.singleelement(pofile)
        assert pounit.getnotes("developer") == "## @name GENERIC_ERROR\n## @loc none"

    def test_folding_accesskeys(self):
        """check that we can fold various accesskeys into their associated label (bug #115)"""
        propsource = r'''cmd_addEngine.label = Add Engines...
cmd_addEngine.accesskey = A'''
        pofile = self.prop2po(propsource, personality="mozilla")
        pounit = self.singleelement(pofile)
        assert pounit.source == "&Add Engines..."

    def test_dont_translate(self):
        """check that we know how to ignore don't translate instructions in properties files (bug #116)"""
        propsource = '''# LOCALIZATION NOTE (dont): DONT_TRANSLATE.
dont=don't translate me
do=translate me
'''
        pofile = self.prop2po(propsource)
        assert self.countelements(pofile) == 1

    def test_emptyproperty(self):
        """checks that empty property definitions survive into po file, bug 15"""
        for delimiter in ["=", ""]:
            propsource = '# comment\ncredit%s' % delimiter
            pofile = self.prop2po(propsource)
            pounit = self.singleelement(pofile)
            assert pounit.getlocations() == ["credit"]
            assert pounit.getcontext() == "credit"
            assert 'msgctxt "credit"' in str(pounit)
            assert b"#. # comment" in bytes(pofile)
            assert pounit.source == ""

    def test_emptyproperty_translated(self):
        """checks that if we translate an empty property it makes it into the PO"""
        for delimiter in ["=", ""]:
            proptemplate = 'credit%s' % delimiter
            propsource = 'credit=Translators Names'
            pofile = self.prop2po(propsource, proptemplate)
            pounit = self.singleelement(pofile)
            assert pounit.getlocations() == ["credit"]
            # FIXME we don't seem to get a _: comment but we should
            #assert pounit.getcontext() == "credit"
            assert pounit.source == ""
            assert pounit.target == "Translators Names"

    def test_newlines_in_value(self):
        """check that we can carry newlines that appear in the property value into the PO"""
        propsource = '''prop=\\nvalue\\n\n'''
        pofile = self.prop2po(propsource)
        unit = self.singleelement(pofile)
        assert unit.source == "\nvalue\n"

    def test_unassociated_comments(self):
        """check that we can handle comments not directly associated with a property"""
        propsource = '''# Header comment\n\n# Comment\n\nprop=value\n'''
        pofile = self.prop2po(propsource)
        unit = self.singleelement(pofile)
        assert unit.source == "value"
        assert unit.getnotes("developer") == "# Comment"

    def test_unassociated_comment_order(self):
        """check that we can handle the order of unassociated comments"""
        propsource = '''# Header comment\n\n# 1st Unassociated comment\n\n# 2nd Connected comment\nprop=value\n'''
        pofile = self.prop2po(propsource)
        unit = self.singleelement(pofile)
        assert unit.source == "value"
        assert unit.getnotes("developer") == "# 1st Unassociated comment\n# 2nd Connected comment"

    def test_x_header(self):
        """Test that we correctly create the custom header entries
        (accelerators, merge criterion).
        """
        propsource = '''prop=value\n'''

        outputpo = self.prop2po(propsource, personality="mozilla")
        assert b"X-Accelerator-Marker" in bytes(outputpo)
        assert b"X-Merge-On" in bytes(outputpo)

        # Even though the gaia flavour inherrits from mozilla, it should not
        # get the header
        outputpo = self.prop2po(propsource, personality="gaia")
        assert b"X-Accelerator-Marker" not in bytes(outputpo)
        assert b"X-Merge-On" not in bytes(outputpo)

    def test_gaia_plurals(self):
        """Test conversion of gaia plural units."""
        propsource = '''
message-multiedit-header={[ plural(n) ]}
message-multiedit-header[zero]=Edit
message-multiedit-header[one]={{ n }} selected
message-multiedit-header[two]={{ n }} selected
message-multiedit-header[few]={{ n }} selected
message-multiedit-header[many]={{ n }} selected
message-multiedit-header[other]={{ n }} selected
'''
        outputpo = self.prop2po(propsource, personality="gaia")
        pounit = outputpo.units[-1]
        assert pounit.hasplural()
        assert pounit.getlocations() == [u'message-multiedit-header']

        print(outputpo)
        zero_unit = outputpo.units[-2]
        assert not zero_unit.hasplural()
        assert zero_unit.source == u"Edit"

    def test_successive_gaia_plurals(self):
        """Test conversion of two successive gaia plural units."""
        propsource = '''
message-multiedit-header={[ plural(n) ]}
message-multiedit-header[zero]=Edit
message-multiedit-header[one]={{ n }} selected
message-multiedit-header[two]={{ n }} selected
message-multiedit-header[few]={{ n }} selected
message-multiedit-header[many]={{ n }} selected
message-multiedit-header[other]={{ n }} selected

message-multiedit-header2={[ plural(n) ]}
message-multiedit-header2[zero]=Edit 2
message-multiedit-header2[one]={{ n }} selected 2
message-multiedit-header2[two]={{ n }} selected 2
message-multiedit-header2[few]={{ n }} selected 2
message-multiedit-header2[many]={{ n }} selected 2
message-multiedit-header2[other]={{ n }} selected 2
'''
        outputpo = self.prop2po(propsource, personality="gaia")
        pounit = outputpo.units[-1]
        assert pounit.hasplural()
        assert pounit.getlocations() == [u'message-multiedit-header2']

        pounit = outputpo.units[-3]
        assert pounit.hasplural()
        assert pounit.getlocations() == [u'message-multiedit-header']

        print(outputpo)
        zero_unit = outputpo.units[-2]
        assert not zero_unit.hasplural()
        assert zero_unit.source == u"Edit 2"

        zero_unit = outputpo.units[-4]
        assert not zero_unit.hasplural()
        assert zero_unit.source == u"Edit"


class TestProp2POCommand(test_convert.TestConvertCommand, TestProp2PO):
    """Tests running actual prop2po commands on files"""
    convertmodule = prop2po
    defaultoptions = {"progress": "none"}

    def test_help(self):
        """tests getting help"""
        options = test_convert.TestConvertCommand.test_help(self)
        options = self.help_check(options, "-P, --pot")
        options = self.help_check(options, "-t TEMPLATE, --template=TEMPLATE")
        options = self.help_check(options, "--personality=TYPE")
        options = self.help_check(options, "--encoding=ENCODING")
        options = self.help_check(options, "--duplicates=DUPLICATESTYLE", last=True)
