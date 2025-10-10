# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "lxml",
# ]
# ///
import shutil
from sys import argv
from tempfile import mkstemp
from zipfile import ZipFile

from lxml import etree

vsix_path = argv[1]

temp_vsix_path = mkstemp("new.vsix")[1]


with ZipFile(vsix_path, "r") as source_vsix, ZipFile(temp_vsix_path, "w") as temp_vsix:
    for item in source_vsix.infolist():
        content = source_vsix.read(item.filename)

        if item.filename == "extension.vsixmanifest":
            tree = etree.fromstring(
                content, parser=etree.XMLParser(remove_blank_text=False)
            )

            tree.find(
                ".//vsx:Identity",
                {"vsx": "http://schemas.microsoft.com/developer/vsx-schema/2011"},
            ).set("TargetPlatform", "linux-loong64")

            temp_vsix.writestr(
                item.filename,
                etree.tostring(
                    tree, xml_declaration=True, encoding="utf-8", pretty_print=False
                ),
            )
        else:
            temp_vsix.writestr(item, content)

shutil.move(temp_vsix_path, vsix_path)
