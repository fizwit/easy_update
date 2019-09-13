#!/usr/bin/env python


import os
import sys
import platform

from parsley import makeGrammar


class PEP_508():
    """ PEP 508 grammar parser written in Parsley
    copied from PEP 508 https://www.python.org/dev/peps/pep-0508/

    return a tuple of tokens.  Example
    marker = "keepalive (>=0.5); extra == 'keepalive'"
    output: ('keepalive', [], [('>=', '0.5')], ('==', 'all', 'keepalive'))
    """
    def __init__(self):


        """platform_release, platform_system, implementation_name, and implementation_version
           which are not present in older marker implementations. The variables will error on
           those implementations.
           **Assume** cpython if "implementation_name" is not defined 
        """
        if hasattr(sys, 'implementation'):
            implementation_version = self.format_full_version(sys.implementation.version)
            implementation_name = sys.implementation.name
        else:
            implementation_version = '0'
            implementation_name = 'cpython'

        self.bindings = {
            'extra': 'all',
            'implementation_name': implementation_name,
            'implementation_version': implementation_version,
            'os_name': os.name,
            'platform_machine': platform.machine(),
            'platform_python_implementation': platform.python_implementation(),
            'platform_release': platform.release(),
            'platform_system': platform.system(),
            'platform_version': platform.version(),
            'python_full_version': platform.python_version(),
            'python_version': '.'.join(platform.python_version_tuple()[:2]),
            'sys_platform': sys.platform,
        }

        self.grammar = """
wsp           = ' ' | '\t'
version_cmp   = wsp* <'<=' | '<' | '!=' | '==' | '>=' | '>' | '~=' | '==='>
version       = wsp* <( letterOrDigit | '-' | '_' | '.' | '*' | '+' | '!' )+>
version_one   = version_cmp:op version:v wsp* -> (op, v)
version_many  = version_one:v1 (wsp* ',' version_one)*:v2 -> [v1] + v2
versionspec   = ('(' version_many:v ')' ->v) | version_many
urlspec       = '@' wsp* <URI_reference>
marker_op     = version_cmp | (wsp* 'in') | (wsp* 'not' wsp+ 'in')
python_str_c  = (wsp | letter | digit | '(' | ')' | '.' | '{' | '}' |
                 '-' | '_' | '*' | '#' | ':' | ';' | ',' | '/' | '?' |
                 '[' | ']' | '!' | '~' | '`' | '@' | '$' | '%' | '^' |
                 '&' | '=' | '+' | '|' | '<' | '>' )
dquote        = '"'
squote        = '\\''
python_str    = (squote <(python_str_c | dquote)*>:s squote |
                 dquote <(python_str_c | squote)*>:s dquote) -> s
env_var       = ('python_version' | 'python_full_version' |
                 'os_name' | 'sys_platform' | 'platform_release' |
                 'platform_system' | 'platform_version' |
                 'platform_machine' | 'platform_python_implementation' |
                 'implementation_name' | 'implementation_version' |
                 'extra' # ONLY when defined by a containing layer
                 ):varname -> lookup(varname)
marker_var    = wsp* (env_var | python_str)
marker_expr   = marker_var:l marker_op:o marker_var:r -> (o, l, r)
              | wsp* '(' marker:m wsp* ')' -> m
marker_and    = marker_expr:l wsp* 'and' marker_expr:r -> ('and', l, r)
              | marker_expr:m -> m
marker_or     = marker_and:l wsp* 'or' marker_and:r -> ('or', l, r)
                  | marker_and:m -> m
marker        = marker_or
quoted_marker = ';' wsp* marker
identifier_end = letterOrDigit | (('-' | '_' | '.' )* letterOrDigit)
identifier    = < letterOrDigit identifier_end* >
name          = identifier
extras_list   = identifier:i (wsp* ',' wsp* identifier)*:ids -> [i] + ids
extras        = '[' wsp* extras_list?:e wsp* ']' -> e
name_req      = (name:n wsp* extras?:e wsp* versionspec?:v wsp* quoted_marker?:m
                 -> (n, e or [], v or [], m))
url_req       = (name:n wsp* extras?:e wsp* urlspec:v (wsp+ | end) quoted_marker?:m
                 -> (n, e or [], v, m))
specification = wsp* ( url_req | name_req ):s wsp* -> s
# The result is a tuple - name, list-of-extras,
# list-of-version-constraints-or-a-url, marker-ast or None


URI_reference = <URI | relative_ref>
URI           = scheme ':' hier_part ('?' query )? ( '#' fragment)?
hier_part     = ('//' authority path_abempty) | path_absolute | path_rootless | path_empty
absolute_URI  = scheme ':' hier_part ( '?' query )?
relative_ref  = relative_part ( '?' query )? ( '#' fragment )?
relative_part = '//' authority path_abempty | path_absolute | path_noscheme | path_empty
scheme        = letter ( letter | digit | '+' | '-' | '.')*
authority     = ( userinfo '@' )? host ( ':' port )?
userinfo      = ( unreserved | pct_encoded | sub_delims | ':')*
host          = IP_literal | IPv4address | reg_name
port          = digit*
IP_literal    = '[' ( IPv6address | IPvFuture) ']'
IPvFuture     = 'v' hexdig+ '.' ( unreserved | sub_delims | ':')+
IPv6address   = (
                  ( h16 ':'){6} ls32
                  | '::' ( h16 ':'){5} ls32
                  | ( h16 )?  '::' ( h16 ':'){4} ls32
                  | ( ( h16 ':')? h16 )? '::' ( h16 ':'){3} ls32
                  | ( ( h16 ':'){0,2} h16 )? '::' ( h16 ':'){2} ls32
                  | ( ( h16 ':'){0,3} h16 )? '::' h16 ':' ls32
                  | ( ( h16 ':'){0,4} h16 )? '::' ls32
                  | ( ( h16 ':'){0,5} h16 )? '::' h16
                  | ( ( h16 ':'){0,6} h16 )? '::' )
h16           = hexdig{1,4}
ls32          = ( h16 ':' h16) | IPv4address
IPv4address   = dec_octet '.' dec_octet '.' dec_octet '.' dec_octet
nz            = ~'0' digit
dec_octet     = (
                  digit # 0-9
                  | nz digit # 10-99
                  | '1' digit{2} # 100-199
                  | '2' ('0' | '1' | '2' | '3' | '4') digit # 200-249
                  | '25' ('0' | '1' | '2' | '3' | '4' | '5') )# %250-255
reg_name = ( unreserved | pct_encoded | sub_delims)*
path = (
        path_abempty # begins with '/' or is empty
        | path_absolute # begins with '/' but not '//'
        | path_noscheme # begins with a non-colon segment
        | path_rootless # begins with a segment
        | path_empty ) # zero characters
path_abempty  = ( '/' segment)*
path_absolute = '/' ( segment_nz ( '/' segment)* )?
path_noscheme = segment_nz_nc ( '/' segment)*
path_rootless = segment_nz ( '/' segment)*
path_empty    = pchar{0}
segment       = pchar*
segment_nz    = pchar+
segment_nz_nc = ( unreserved | pct_encoded | sub_delims | '@')+
                # non-zero-length segment without any colon ':'
pchar         = unreserved | pct_encoded | sub_delims | ':' | '@'
query         = ( pchar | '/' | '?')*
fragment      = ( pchar | '/' | '?')*
pct_encoded   = '%' hexdig
unreserved    = letter | digit | '-' | '.' | '_' | '~'
reserved      = gen_delims | sub_delims
gen_delims    = ':' | '/' | '?' | '#' | '(' | ')?' | '@'
sub_delims    = '!' | '$' | '&' | '\\'' | '(' | ')' | '*' | '+' | ',' | ';' | '='
hexdig        = digit | 'a' | 'A' | 'b' | 'B' | 'c' | 'C' | 'd' | 'D' | 'e' | 'E' | 'f' | 'F'
"""
        self.compiled = makeGrammar(self.grammar, {'lookup': self.bindings.__getitem__})
        #return self.compiled

    def format_full_version(self, info):
        version = '{0.major}.{0.minor}.{0.micro}'.format(info)
        kind = info.releaselevel
        if kind != 'final':
            version += kind[0] + str(info.serial)
        return version

    def bindings(self):
        return self.bindings

    def parse(self, marker):
        return self.compiled(marker).specification()




if __name__ == '__main__':
    tests = [
        "A",
        "A.B-C_D",
        "aa",
        "name",
        "name<=1",
        "name>=3",
        "name>=3,<2",
        "name@http://foo.com",
        "name [fred,bar] @ http://foo.com ; python_version=='2.7'",
        "name[quux, strange];python_version<'2.7' and platform_version=='2'",
        "name; os_name=='a' or os_name=='b'",
        # Should parse as (a and b) or c
        "name; os_name=='a' and os_name=='b' or os_name=='c'",
        # Overriding precedence -> a and (b or c)
        "name; os_name=='a' and (os_name=='b' or os_name=='c')",
        # should parse as a or (b and c)
        "name; os_name=='a' or os_name=='b' and os_name=='c'",
        # Overriding precedence -> (a or b) and c
        "name; (os_name=='a' or os_name=='b') and os_name=='c'",
        "keepalive (>=0.5); extra == 'keepalive'"
        ]

    pep_508 = PEP_508()

    for test in tests:
        print('Parsing: {}'.format(test))
        parsed = pep_508.parse(test)
        print("len({}) {} -> {}".format(len(parsed), test, parsed))
