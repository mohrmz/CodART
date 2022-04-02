"""
Extract subclass refactoring
"""


import os
from gen.javaLabeled.JavaLexer import JavaLexer
from antlr4 import *
from antlr4.tree import Tree
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener

files_to_refactor = []


class ExtractSubClassRefactoringListener(JavaParserLabeledListener):
    """
    To implement extract class refactoring based on its actors.
    Creates a new class and move fields and methods from the old class to the new one
    """

    def __init__(
            self, common_token_stream: CommonTokenStream = None,
            source_class: str = None, new_class: str = None,
            moved_fields=None, moved_methods=None,
            output_path: str = ""):

        if moved_methods is None:
            self.moved_methods = []
        else:
            self.moved_methods = moved_methods
        if moved_fields is None:
            self.moved_fields = []
        else:
            self.moved_fields = moved_fields

        if common_token_stream is None:
            raise ValueError('common_token_stream is None')
        else:
            self.token_stream_rewriter = TokenStreamRewriter(common_token_stream)

        if source_class is None:
            raise ValueError("source_class is None")
        else:
            self.source_class = source_class
        if new_class is None:
            raise ValueError("new_class is None")
        else:
            self.new_class = new_class

        self.output_path = output_path

        self.is_source_class = False
        self.detected_field = None
        self.detected_method = None
        self.TAB = "\t"
        self.NEW_LINE = "\n"
        self.code = ""
        self.is_in_constructor = False

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        """
        It checks if it is source class, we generate the declaration of the new class, by appending some text to self.code.
        """
        class_identifier = ctx.IDENTIFIER().getText()
        if class_identifier == self.source_class:
            self.is_source_class = True
            self.code += self.NEW_LINE * 2
            self.code += f"// New class({self.new_class}) generated by CodART" + self.NEW_LINE
            self.code += f"class {self.new_class} extends {self.source_class}{self.NEW_LINE}" + "{" + self.NEW_LINE
            self.code += f"public {self.new_class}()" + "{ }" + self.NEW_LINE
        else:
            self.is_source_class = False

    def exitClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        """
        It close the opened curly brackets If it is the source class.
        """
        if self.is_source_class:
            self.code += "}"
            self.is_source_class = False

    def exitCompilationUnit(self, ctx: JavaParserLabeled.CompilationUnitContext):
        """
        it writes self.code in the output path.​
        """
        child_file_name = self.new_class + ".java"
        with open(os.path.join(self.output_path, child_file_name), "w+") as f:
            f.write(self.code.replace('\r\n', '\n'))

    def enterVariableDeclaratorId(self, ctx: JavaParserLabeled.VariableDeclaratorIdContext):
        """
        It sets the detected field to the field if it is one of the moved fields. ​
        """
        if not self.is_source_class:
            return None
        field_identifier = ctx.IDENTIFIER().getText()
        if field_identifier in self.moved_fields:
            self.detected_field = field_identifier

    def exitFieldDeclaration(self, ctx: JavaParserLabeled.FieldDeclarationContext):
        """
        It gets the field name, if the field is one of the moved fields, we move it and delete it from the source program. ​
        """
        if not self.is_source_class:
            return None
        field_identifier = ctx.variableDeclarators().variableDeclarator(0).variableDeclaratorId().IDENTIFIER().getText()
        field_names = list()
        field_names.append(field_identifier)
        # print("field_names=", field_names)
        grand_parent_ctx = ctx.parentCtx.parentCtx
        if self.detected_field in field_names:
            if (not grand_parent_ctx.modifier()):
                modifier = ""
            else:
                modifier = grand_parent_ctx.modifier(0).getText()
            field_type = ctx.typeType().getText()
            self.code += f"{self.TAB}{modifier} {field_type} {self.detected_field};{self.NEW_LINE}"

            # delete field from source class ==>new
            start_index = ctx.parentCtx.parentCtx.start.tokenIndex
            stop_index = ctx.parentCtx.parentCtx.stop.tokenIndex
            self.token_stream_rewriter.delete(
                program_name=self.token_stream_rewriter.DEFAULT_PROGRAM_NAME,
                from_idx=start_index,
                to_idx=stop_index
            )

            self.detected_field = None

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        """
        It sets the detected field to the method if it is one of the moved methods. ​
        """
        if not self.is_source_class:
            return None
        method_identifier = ctx.IDENTIFIER().getText()
        if method_identifier in self.moved_methods:
            self.detected_method = method_identifier

    def exitMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        """
        It gets the method name, if the method is one of the moved methods, we move it to the subclass and delete it from the source program.
        """
        if not self.is_source_class:
            return None
        method_identifier = ctx.IDENTIFIER().getText()
        if self.detected_method == method_identifier:
            start_index = ctx.parentCtx.parentCtx.start.tokenIndex
            stop_index = ctx.stop.tokenIndex
            method_text = self.token_stream_rewriter.getText(
                program_name=self.token_stream_rewriter.DEFAULT_PROGRAM_NAME,
                start=start_index,
                stop=stop_index
            )
            self.code += (self.NEW_LINE + self.TAB + method_text + self.NEW_LINE)
            # delete method from source class
            self.token_stream_rewriter.delete(
                program_name=self.token_stream_rewriter.DEFAULT_PROGRAM_NAME,
                from_idx=start_index,
                to_idx=stop_index
            )
            self.detected_method = None

    def enterConstructorDeclaration(self, ctx: JavaParserLabeled.ConstructorDeclarationContext):
        if self.is_source_class:
            self.is_in_constructor = True
            self.fields_in_constructor = []
            self.methods_in_constructor = []
            self.constructor_body = ctx.block()
            children = self.constructor_body.children

    def exitConstructorDeclaration(self, ctx: JavaParserLabeled.ConstructorDeclarationContext):
        if self.is_source_class and self.is_in_constructor:
            move_constructor_flag = False
            for field in self.fields_in_constructor:
                if field in self.moved_fields:
                    move_constructor_flag = True

            for method in self.methods_in_constructor:
                if method in self.moved_methods:
                    move_constructor_flag = True

            if move_constructor_flag:
                if ctx.formalParameters().formalParameterList():
                    constructor_parameters = [ctx.formalParameters().formalParameterList().children[i] for i in
                                              range(len(ctx.formalParameters().formalParameterList().children)) if
                                              i % 2 == 0]
                else:
                    constructor_parameters = []

                constructor_text = ''
                for modifier in ctx.parentCtx.parentCtx.modifier():
                    constructor_text += modifier.getText() + ' '
                constructor_text += self.new_class
                constructor_text += ' ( '
                for parameter in constructor_parameters:
                    constructor_text += parameter.typeType().getText() + ' '
                    constructor_text += parameter.variableDeclaratorId().getText() + ', '
                if constructor_parameters:
                    constructor_text = constructor_text[:len(constructor_text) - 2]
                constructor_text += ')\n\t{'
                constructor_text += self.token_stream_rewriter.getText(
                    program_name=self.token_stream_rewriter.DEFAULT_PROGRAM_NAME,
                    start=ctx.block().start.tokenIndex + 1,
                    stop=ctx.block().stop.tokenIndex - 1
                )
                constructor_text += '}\n'
                self.code += constructor_text
                start_index = ctx.parentCtx.parentCtx.start.tokenIndex
                stop_index = ctx.parentCtx.parentCtx.stop.tokenIndex
                self.token_stream_rewriter.delete(
                    program_name=self.token_stream_rewriter.DEFAULT_PROGRAM_NAME,
                    from_idx=start_index,
                    to_idx=stop_index
                )

        self.is_in_constructor = False

    def enterExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        if self.is_source_class and self.is_in_constructor:
            if len(ctx.children[0].children) == 1:
                self.fields_in_constructor.append(ctx.children[0].getText())
            else:
                self.fields_in_constructor.append(ctx.children[0].children[-1].getText())

    def enterMethodCall0(self, ctx: JavaParserLabeled.MethodCall0Context):
        if self.is_source_class and self.is_in_constructor:
            self.methods_in_constructor.append(ctx.IDENTIFIER())


class FindUsagesListener(JavaParserLabeledListener):
    def __init__(
            self, common_token_stream: CommonTokenStream = None,
            source_class: str = None, new_class: str = None,
            moved_fields=None, moved_methods=None,
            output_path: str = ""):

        if moved_methods is None:
            self.moved_methods = []
        else:
            self.moved_methods = moved_methods

        if moved_fields is None:
            self.moved_fields = []
        else:
            self.moved_fields = moved_fields

        if common_token_stream is None:
            raise ValueError('common_token_stream is None')
        else:
            self.token_stream_rewriter = TokenStreamRewriter(common_token_stream)

        if source_class is None:
            raise ValueError("source_class is None")
        else:
            self.source_class = source_class

        if new_class is None:
            raise ValueError("new_class is None")
        else:
            self.new_class = new_class

        self.output_path = output_path

        self.is_source_class = False
        self.detected_field = None
        self.detected_method = None
        self.TAB = "\t"
        self.NEW_LINE = "\n"
        self.code = ""
        self.scope = []
        self.aul = AllUsageList()

    def exitTypeTypeOrVoid(self, ctx: JavaParserLabeled.TypeTypeOrVoidContext):
        if ctx.getText() == self.source_class:
            self.token_stream_rewriter.replaceRange(
                from_idx=ctx.start.tokenIndex,
                to_idx=ctx.stop.tokenIndex,
                text=f"{self.new_class}"
            )

    def exitFormalParameter(self, ctx: JavaParserLabeled.FormalParameterContext):
        if ctx.typeType().getText() == self.source_class:
            self.token_stream_rewriter.replaceRange(
                from_idx=ctx.typeType().start.tokenIndex,
                to_idx=ctx.typeType().stop.tokenIndex,
                text=f"{self.new_class}"
            )

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.scope.append(f"class:{ctx.IDENTIFIER().getText()}")

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.scope.append(f"method:{ctx.IDENTIFIER().getText()}")

    def exitClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.scope.pop()

    def exitMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.scope.pop()

    def exitFieldDeclaration(self, ctx: JavaParserLabeled.FieldDeclarationContext):
        if ctx.typeType().getText() == self.source_class:
            self.aul.add_identifier(
                (ctx.variableDeclarators().variableDeclarator(0).variableDeclaratorId().IDENTIFIER().getText(),
                 self.scope))

    def exitLocalVariableDeclaration(self, ctx: JavaParserLabeled.LocalVariableDeclarationContext):
        if (ctx.typeType().getText() == self.source_class):
            self.aul.add_identifier(
                (ctx.variableDeclarators().variableDeclarator(0).variableDeclaratorId().IDENTIFIER().getText(),
                 self.scope))

    def exitExpression1(self, ctx: JavaParserLabeled.Expression1Context):
        # left_hand_side'.'right_hand_side  ==> identifier.method | identifier.field
        right_hand_side = ctx.children[-1]
        left_hand_side = ctx.children[0]
        if type(left_hand_side) == JavaParserLabeled.Expression0Context:
            if type(right_hand_side) == Tree.TerminalNodeImpl:
                if left_hand_side.getText() != 'this':
                    self.aul.add_field_to_identifier(identifier=(left_hand_side.getText(), self.scope),
                                                     field_name=right_hand_side.getText())
            elif type(right_hand_side) == JavaParserLabeled.MethodCall0Context:
                if left_hand_side.getText() != 'this':
                    self.aul.add_method_to_identifier(identifier=(left_hand_side.getText(), self.scope),
                                                      method_name=right_hand_side.children[0].getText())

        elif type(left_hand_side) == JavaParserLabeled.Expression1Context:
            if type(right_hand_side) == Tree.TerminalNodeImpl:
                self.aul.add_field_to_identifier(identifier=(left_hand_side.children[-1].getText(), self.scope),
                                                 field_name=right_hand_side.getText())
            elif type(right_hand_side) == JavaParserLabeled.MethodCall0Context:
                self.aul.add_method_to_identifier(identifier=(left_hand_side.children[-1].getText(), self.scope),
                                                  method_name=right_hand_side.children[0].getText())


class PropagationListener(JavaParserLabeledListener):
    def __init__(
            self, common_token_stream: CommonTokenStream = None,
            source_class: str = None, new_class: str = None,
            moved_fields=None, moved_methods=None,
            output_path: str = "", aul=None):

        if moved_methods is None:
            self.moved_methods = []
        else:
            self.moved_methods = moved_methods

        if moved_fields is None:
            self.moved_fields = []
        else:
            self.moved_fields = moved_fields

        if common_token_stream is None:
            raise ValueError('common_token_stream is None')
        else:
            self.token_stream_rewriter = TokenStreamRewriter(common_token_stream)

        if source_class is None:
            raise ValueError("source_class is None")
        else:
            self.source_class = source_class

        if new_class is None:
            raise ValueError("new_class is None")
        else:
            self.new_class = new_class

        self.output_path = output_path

        self.is_source_class = False
        self.detected_field = None
        self.detected_method = None
        self.TAB = "\t"
        self.NEW_LINE = "\n"
        self.code = ""
        self.scope = []
        self.aul = aul

    def intersection(self, lst1, lst2):
        lst3 = [value for value in lst1 if value in lst2]
        return lst3

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.scope.append(f"class:{ctx.IDENTIFIER().getText()}")

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.scope.append(f"method:{ctx.IDENTIFIER().getText()}")

    def exitClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.scope.pop()

    def exitMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.scope.pop()

    def exitFieldDeclaration(self, ctx: JavaParserLabeled.FieldDeclarationContext):
        if ctx.typeType().getText() == self.source_class:
            flag = False
            for child in ctx.variableDeclarators().children:
                if child.getText() != ',':
                    id = child.variableDeclaratorId().IDENTIFIER().getText()
                    fields_used = self.aul.get_identifier_fields((id, self.scope))
                    methods_used = self.aul.get_identifier_methods((id, self.scope))

                    if len(self.intersection(fields_used, self.moved_fields)) > 0 or len(
                            self.intersection(methods_used, self.moved_methods)) > 0:
                        flag = True

            if flag == True:
                self.token_stream_rewriter.replaceRange(
                    from_idx=ctx.typeType().start.tokenIndex,
                    to_idx=ctx.typeType().stop.tokenIndex,
                    text=f"{self.new_class}"
                )

                for child in ctx.variableDeclarators().children:
                    if child.getText() != ',':
                        if type(child.children[-1]) == JavaParserLabeled.VariableInitializer1Context and \
                                type(child.children[-1].children[0]) == JavaParserLabeled.Expression4Context and \
                                child.children[-1].children[0].children[0].getText() == 'new' and \
                                len(child.children[-1].children[0].children) > 1 and \
                                type(child.children[-1].children[0].children[1]) == JavaParserLabeled.Creator1Context:
                            if child.variableInitializer().expression().creator().createdName().getText() == self.source_class:
                                self.token_stream_rewriter.replaceRange(
                                    from_idx=child.variableInitializer().expression().creator().createdName().start.tokenIndex,
                                    to_idx=child.variableInitializer().expression().creator().createdName().stop.tokenIndex,
                                    text=f"{self.new_class}"
                                )

    def exitLocalVariableDeclaration(self, ctx: JavaParserLabeled.LocalVariableDeclarationContext):
        if ctx.typeType().getText() == self.source_class:
            flag = False
            for child in ctx.variableDeclarators().children:
                if child.getText() != ',':
                    id = child.variableDeclaratorId().IDENTIFIER().getText()
                    fields_used = self.aul.get_identifier_fields((id, self.scope))
                    methods_used = self.aul.get_identifier_methods((id, self.scope))

                    if len(self.intersection(fields_used, self.moved_fields)) > 0 or len(
                            self.intersection(methods_used, self.moved_methods)) > 0:
                        flag = True

            if flag == True:
                self.token_stream_rewriter.replaceRange(
                    from_idx=ctx.typeType().start.tokenIndex,
                    to_idx=ctx.typeType().stop.tokenIndex,
                    text=f"{self.new_class}"
                )

                for child in ctx.variableDeclarators().children:
                    if child.getText() != ',':
                        if type(child.children[-1]) == JavaParserLabeled.VariableInitializer1Context and \
                                type(child.children[-1].children[0]) == JavaParserLabeled.Expression4Context and \
                                child.children[-1].children[0].children[0].getText() == 'new' and \
                                len(child.children[-1].children[0].children) > 1 and \
                                type(child.children[-1].children[0].children[1]) == JavaParserLabeled.Creator1Context:
                            if child.variableInitializer().expression().creator().createdName().getText() == self.source_class:
                                self.token_stream_rewriter.replaceRange(
                                    from_idx=child.variableInitializer().expression().creator().createdName().start.tokenIndex,
                                    to_idx=child.variableInitializer().expression().creator().createdName().stop.tokenIndex,
                                    text=f"{self.new_class}"
                                )


def main():
    """
    it builds the parse tree and walk its corresponding walker so that our overridden methods run.
    """

    # udb_path = "/home/ali/Desktop/code/TestProject/TestProject.udb"
    # udb_path=create_understand_database("C:\\Users\\asus\\Desktop\\test_project")
    # source_class = "GodClass"
    # moved_methods = ['method1', 'method3', ]
    # moved_fields = ['field1', 'field2', ]
    udb_path = "C:\\Users\\asus\\Desktop\\test_project\\test_project.udb"
    # moved_methods = ['getValue', 'rowToJSONArray', 'getVal', ]
    # moved_fields = ['number_2', 'number_1', ]

    source_class = "GodClass"
    moved_methods = ['method1', 'method3']
    moved_fields = ['field1', 'field2']
    father_path_file = "/data/Dev/JavaSample/src/GodClass.java"
    father_path_directory = "/data/Dev/JavaSample/src"
    path_to_refactor = "/data/Dev/JavaSample/src"
    new_class_file = "/data/Dev/JavaSample/src/GodSubClass.java"

    # source_class = "TaskNode"
    # moved_methods = ['getUserObject']
    # moved_fields = []
    # father_path_file = "C:\\Users\\asus\\Desktop\\benchmark_projects\\ganttproject\\ganttproject\\src\\main\\java\\net\\sourceforge\\ganttproject\\task\\TaskNode.java"
    # father_path_directory = "C:\\Users\\asus\\Desktop\\benchmark_projects\\ganttproject\\ganttproject\\src\\main\\java\\net\\sourceforge\\ganttproject\\task"
    # path_to_refactor = "C:\\Users\\asus\\Desktop\\benchmark_projects\\ganttproject"
    # new_class_file = "C:\\Users\\asus\\Desktop\\benchmark_projects\\ganttproject\\ganttproject\\src\\main\\java\\net\\sourceforge\\ganttproject\\task\\TaskNodeextracted.java"

    # source_class = "SecuritySupport"
    # moved_methods = ['getSystemProperty']
    # moved_fields = []
    # father_path_file = "C:\\Users\\asus\\Desktop\\benchmark_projects\\xerces2-j\\src\\org\\apache\\html\\dom\\SecuritySupport.java"
    # father_path_directory = "C:\\Users\\asus\\Desktop\\benchmark_projects\\xerces2-j\\src\\org\\apache\\html\\dom"
    # path_to_refactor = "C:\\Users\\asus\\Desktop\\benchmark_projects\\xerces2-j"
    # new_class_file = "C:\\Users\\asus\\Desktop\\benchmark_projects\\xerces2-j\\src\\org\\apache\\html\\dom\\SecuritySupportextracted.java"

    # source_class = "BaseMarkupSerializer"
    # moved_methods = ['setOutputCharStream']
    # moved_fields = []
    # father_path_file = "C:\\Users\\asus\\Desktop\\benchmark_projects\\xerces2-j\\src\\org\\apache\\xml\\serialize\\BaseMarkupSerializer.java"
    # father_path_directory = "C:\\Users\\asus\\Desktop\\benchmark_projects\\xerces2-j\\src\\org\\apache\\xml\\serialize"
    # path_to_refactor = "C:\\Users\\asus\\Desktop\\benchmark_projects\\xerces2-j"
    # new_class_file = "C:\\Users\\asus\\Desktop\\benchmark_projects\\xerces2-j\\src\\org\\apache\\xml\\serialize\\BaseMarkupSerializerextracted.java"

    # source_class = "Piece"
    # moved_methods = ['setX']
    # moved_fields = []
    # father_path_file = "C:\\Users\\asus\\Desktop\\benchmark_projects\\Chess_master\\src\\game\\Piece.java"
    # father_path_directory = "C:\\Users\\asus\\Desktop\\benchmark_projects\\Chess_master\\src\\game"
    # path_to_refactor = "C:\\Users\\asus\\Desktop\\benchmark_projects\\Chess_master"
    # new_class_file = "C:\\Users\\asus\\Desktop\\benchmark_projects\\Chess_master\\src\\game\\Pieceextracted.java"

    stream = FileStream(father_path_file, encoding='utf8', errors='ignore')
    lexer = JavaLexer(stream)
    token_stream = CommonTokenStream(lexer)
    parser = JavaParserLabeled(token_stream)
    parser.getTokenStream()
    parse_tree = parser.compilationUnit()
    my_listener = ExtractSubClassRefactoringListener(common_token_stream=token_stream,
                                                     source_class=source_class,
                                                     new_class=source_class + "extracted",
                                                     moved_fields=moved_fields, moved_methods=moved_methods,
                                                     output_path=father_path_directory)
    walker = ParseTreeWalker()
    walker.walk(t=parse_tree, listener=my_listener)

    with open(father_path_file, mode='w', newline='') as f:
        f.write(my_listener.token_stream_rewriter.getDefaultText())

    extractJavaFilesAndProcess(path_to_refactor, father_path_file, new_class_file)

    for file in files_to_refactor:
        stream = FileStream(file, encoding='utf8', errors='ignore')
        lexer = JavaLexer(stream)
        token_stream = CommonTokenStream(lexer)
        parser = JavaParserLabeled(token_stream)
        parser.getTokenStream()
        parse_tree = parser.compilationUnit()

        my_listener = FindUsagesListener(common_token_stream=token_stream,
                                         source_class=source_class,
                                         new_class=source_class + "extracted",
                                         moved_fields=moved_fields, moved_methods=moved_methods,
                                         output_path=father_path_directory)

        # output_path=father_path_directory)

        walker = ParseTreeWalker()
        walker.walk(t=parse_tree, listener=my_listener)

        tmp_aul = my_listener.aul

        with open(file, mode='w', newline='') as f:
            f.write(my_listener.token_stream_rewriter.getDefaultText())

        # after find usages

        try:
            stream = FileStream(file, encoding='utf8', errors='ignore')
            lexer = JavaLexer(stream)
            token_stream = CommonTokenStream(lexer)
            parser = JavaParserLabeled(token_stream)
            parser.getTokenStream()
            parse_tree = parser.compilationUnit()

            my_listener = PropagationListener(common_token_stream=token_stream,
                                              source_class=source_class,
                                              new_class=source_class + "extracted",
                                              moved_fields=moved_fields, moved_methods=moved_methods,
                                              output_path=father_path_directory, aul=tmp_aul)

            walker = ParseTreeWalker()
            walker.walk(t=parse_tree, listener=my_listener)

            with open(file, mode='w', newline='') as f:
                f.write(my_listener.token_stream_rewriter.getDefaultText())
        except:
            print("not utf8")


class IdentifierUsage:
    def __init__(self):
        self.file_name = ""
        self.identifier = ""
        self.methods_used = []
        self.fields_used = []
        self.identifier_type = ""
        self.scope = []

    def set_scope(self, scp):
        self.scope = scp

    def is_in_methods_used(self, method_name: str):
        return method_name in self.methods_used

    def is_in_fields_used(self, field_name: str):
        return field_name in self.fields_used

    def add_method(self, method_name: str):
        if not self.is_in_methods_used(method_name):
            self.methods_used.append(method_name)

    def add_field(self, field_name: str):
        if not self.is_in_fields_used(field_name):
            self.fields_used.append(field_name)

    def set_file_name(self, name: str):
        self.file_name = name

    def set_identifier(self, name: str):
        self.identifier = name

    def add_to_scope(self, type_name: str, name: str):
        self.scope.append(type_name + ":" + name)

    def remove_from_scope(self, type_name: str, name: str):
        item_name = type_name + ":" + name
        if item_name != self.scope[-1]:
            raise Exception("invalid operation on scope")
        else:
            self.scope.pop()

    def get_methods_name(self):
        return self.methods_used

    def get_fields_name(self):
        return self.fields_used

    def get_identifier_name(self):
        return self.identifier

    def get_scope(self):
        return self.scope

    def get_file_name(self):
        return self.file_name

    def get_identifier_type(self):
        return self.identifier_type


class AllUsageList:
    def __init__(self):
        self.all_usage = dict()  # all_usage is a dictionary of IdentifierUsage       tuple(scope,identifier_name) ==> IdentifierUsage()

    def is_already_used(self, identifier_usage: tuple):
        return self.get_tuple(identifier_usage) in self.all_usage

    def get_tuple(self, identifier: tuple):
        return (identifier[0], tuple(identifier[1]))

    def add_identifier(self, identifier: tuple):  # identifier is tuple of (identifier_name,scope)
        self.all_usage[self.get_tuple(identifier)] = IdentifierUsage()

    def add_method_to_identifier(self, identifier: tuple,
                                 method_name: str):  # identifier is tuple of (identifier_name,scope)
        if self.get_tuple(identifier) in self.all_usage:
            self.all_usage[self.get_tuple(identifier)].add_method(method_name)
        else:
            id = identifier[0]
            tmp = identifier[1].copy()
            while len(tmp) > 0:
                tmp.pop()
                if self.get_tuple((id, tmp)) in self.all_usage:
                    self.all_usage[self.get_tuple((id, tmp))].add_method(method_name)
                    break

    def add_field_to_identifier(self, identifier: tuple, field_name: str):
        if self.get_tuple(identifier) in self.all_usage:
            self.all_usage[self.get_tuple(identifier)].add_field(field_name)
        else:
            id = identifier[0]
            tmp = identifier[1].copy()
            while len(tmp) > 0:
                tmp.pop()
                if self.get_tuple((id, tmp)) in self.all_usage:
                    self.all_usage[self.get_tuple((id, tmp))].add_field(field_name)
                    break

    def is_method_of_identifier(self, identifier: tuple, method_name: str):
        return self.get_tuple(identifier) in self.all_usage and self.all_usage[
            self.get_tuple(identifier)].is_in_methods_used(method_name)

    def is_field_of_identifier(self, identifier: tuple, field_name: str):
        return self.get_tuple(identifier) in self.all_usage and self.all_usage[
            self.get_tuple(identifier)].is_in_fields_used(field_name)

    def get_identifier_methods(self, identifier: tuple):
        if self.get_tuple(identifier) in self.all_usage:
            return self.all_usage[self.get_tuple(identifier)].get_methods_name()
        else:
            id = identifier[0]
            tmp = identifier[1].copy()
            while len(tmp) > 0:
                tmp.pop()
                if self.get_tuple((id, tmp)) in self.all_usage:
                    return self.all_usage[self.get_tuple((id, tmp))].get_methods_name()

    def get_identifier_fields(self, identifier: tuple):
        if self.get_tuple(identifier) in self.all_usage:
            return self.all_usage[self.get_tuple(identifier)].get_methods_name()
        else:
            id = identifier[0]
            tmp = identifier[1].copy()
            while len(tmp) > 0:
                tmp.pop()
                if self.get_tuple((id, tmp)) in self.all_usage:
                    return self.all_usage[self.get_tuple((id, tmp))].get_fields_name()


def extractJavaFilesAndProcess(path, source_class_file, new_class_file):
    try:
        entries = os.listdir(path)
        for entry in entries:
            print(entry)
            if (not os.path.isfile(os.path.join(path, entry))):
                extractJavaFilesAndProcess(os.path.join(path, entry), source_class_file, new_class_file)
            else:
                if ('.java' in entry or '.Java' in entry) and str(entry) != source_class_file and str(
                        entry) != new_class_file:
                    files_to_refactor.append(os.path.join(path, entry))
    except:
        print("error to read")


if __name__ == '__main__':
    main()
