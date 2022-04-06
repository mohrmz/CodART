"""
Increase method visibility refactoring

"""

__author__ = "Morteza Zakeri"
__version__ = '0.2.0'

try:
    import understand as und
except ImportError as e:
    print(e)

from antlr4.TokenStreamRewriter import TokenStreamRewriter

from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from codart.symbol_table import parse_and_walk
from sbse.config import logger


class IncreaseMethodVisibilityListener(JavaParserLabeledListener):
    def __init__(self, source_class, source_method, rewriter: TokenStreamRewriter):
        self.source_class = source_class
        self.source_method = source_method
        self.in_class = False
        self.detected_method = False
        self.rewriter = rewriter

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        if ctx.IDENTIFIER().getText() == self.source_class:
            self.in_class = True

    def exitClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        if ctx.IDENTIFIER().getText() == self.source_class:
            self.in_class = False

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        if ctx.IDENTIFIER().getText() == self.source_method:
            self.detected_method = True

    def exitClassBodyDeclaration2(self, ctx: JavaParserLabeled.ClassBodyDeclaration2Context):
        if self.detected_method:
            if ctx.modifier(0) is not None:
                self.rewriter.replaceSingleToken(
                    token=ctx.modifier(0).start,
                    text="public"
                )
            else:
                self.rewriter.replaceSingleToken(
                    ctx.memberDeclaration().start,
                    text="public " + ctx.memberDeclaration().getText()
                )
            self.detected_method = False


def main(udb_path, source_package, source_class, source_method, *args, **kwargs):
    db = und.open(udb_path)
    methods = db.lookup(f"{source_package}.{source_class}.{source_method}", "Method")

    if methods is None or len(methods) == 0:
        logger.error("Invalid inputs.")
        db.close()
        return False

    method_entity = methods[0]
    if method_entity.simplename() != source_method:
        logger.error("Invalid entity.")
        db.close()
        return False

    # Strong overlay precondition
    # if not method_entity.kind().check("Private"):
    #     logger.error("Method is not private.")
    #     db.close()
    #     return False

    parent = method_entity.parent()
    while parent.parent() is not None:
        parent = parent.parent()

    main_file = parent.longname()  # The file that contain the method
    db.close()

    parse_and_walk(
        file_path=main_file,
        listener_class=IncreaseMethodVisibilityListener,
        has_write=True,
        source_class=source_class,
        source_method=source_method
    )
    # db.close()
    return True


if __name__ == '__main__':
    main(
        udb_path="D:\Dev\JavaSample\JavaSample\JavaSample.und",
        source_package="source_package",
        source_class="Sample",
        source_method="testMethod"
    )
