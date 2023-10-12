"""Abstract class for IR Passes for Jac."""
from __future__ import annotations

import pprint
from typing import Generic, Optional, TypeVar, Union

from jaclang.jac.constant import Constants as Con, EdgeDir
from jaclang.jac.constant import Tokens as Tok
from jaclang.jac.symtable import SymbolTable

T = TypeVar("T")


class AstNode:
    """Abstract syntax tree node for Jac."""

    def __init__(self, mod_link: Optional[Module], kid: list[AstNode]) -> None:
        """Initialize ast."""
        self.parent: Optional[AstNode] = None
        self.kid = [x.set_parent(self) for x in kid]
        self.mod_link = mod_link
        self.sym_tab: Optional[SymbolTable] = None
        self._sub_node_tab: dict[AstNode, list[AstNode]] = {}
        self._typ: type = type(None)
        self.meta: dict = {}
        self.tok_range: tuple[Token, Token] = self.resolve_tok_range()

    @property
    def line(self) -> int:
        """Get line number."""
        return self.tok_range[0].line_no

    def add_kids_left(self, nodes: list[AstNode]) -> AstNode:
        """Add kid left."""
        self.kid = [*nodes, *self.kid]
        for i in nodes:
            i.parent = self
        self.tok_range = self.resolve_tok_range()
        return self

    def add_kids_right(self, nodes: list[AstNode]) -> AstNode:
        """Add kid right."""
        self.kid = [*self.kid, *nodes]
        for i in nodes:
            i.parent = self
        self.tok_range = self.resolve_tok_range()
        return self

    def set_kids(self, nodes: list[AstNode]) -> AstNode:
        """Set kids."""
        self.kid = nodes
        for i in nodes:
            i.parent = self
        self.tok_range = self.resolve_tok_range()
        return self

    def set_parent(self, parent: AstNode) -> AstNode:
        """Set parent."""
        self.parent = parent
        return self

    def resolve_tok_range(self) -> tuple[Token, Token]:
        """Get token range."""
        if len(self.kid):
            return (
                self.kid[0].tok_range[0],
                self.kid[-1].tok_range[1],
            )
        elif isinstance(self, Token):
            return (self, self)
        else:
            raise ValueError(f"Empty kid for Token {type(self).__name__}")

    def to_dict(self) -> dict:
        """Return dict representation of node."""
        ret = {
            "node": str(type(self).__name__),
            "kid": [x.to_dict() for x in self.kid if x],
            "line": self.tok_range[0].line,
        }
        if isinstance(self, Token):
            ret["name"] = self.name
            ret["value"] = self.value
        return ret

    def print(self, depth: Optional[int] = None) -> None:
        """Print ast."""
        pprint.PrettyPrinter(depth=depth).pprint(self.to_dict())


# AST Mid Level Node Types
# --------------------------
class Module(AstNode):
    """Whole Program node type for Jac Ast."""

    def __init__(
        self,
        name: str,
        doc: Optional[Constant],
        body: list[ElementStmt],
        mod_path: str,
        rel_mod_path: str,
        is_imported: bool,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize whole program node."""
        self.name = name
        self.doc = doc
        self.body = body
        self.mod_path = mod_path
        self.rel_mod_path = rel_mod_path
        self.is_imported = is_imported
        super().__init__(
            mod_link=mod_link,
            kid=kid,
        )


class GlobalVars(AstNode):
    """GlobalVars node type for Jac Ast."""

    def __init__(
        self,
        access: Optional[SubTag[Token]],
        assignments: SubNodeList[Assignment],
        is_frozen: bool,
        mod_link: Optional[Module],
        kid: list[AstNode],
        doc: Optional[Constant] = None,
    ) -> None:
        """Initialize global var node."""
        self.doc = doc
        self.access = access
        self.assignments = assignments
        self.is_frozen = is_frozen
        super().__init__(mod_link=mod_link, kid=kid)


class SubTag(AstNode, Generic[T]):
    """SubTag node type for Jac Ast."""

    def __init__(
        self,
        tag: T,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize tag node."""
        self.tag = tag
        super().__init__(mod_link=mod_link, kid=kid)


class SubNodeList(AstNode, Generic[T]):
    """SubNodeList node type for Jac Ast."""

    def __init__(
        self,
        items: list[T],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize sub node list node."""
        self.items = items
        super().__init__(mod_link=mod_link, kid=kid)


class Test(AstNode):
    """Test node type for Jac Ast."""

    TEST_COUNT = 0

    def __init__(
        self,
        name: Name | Token,
        body: SubNodeList[CodeBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
        doc: Optional[Constant] = None,
    ) -> None:
        """Initialize test node."""
        self.doc = doc
        Test.TEST_COUNT += 1 if isinstance(name, Token) else 0
        self.name: Name = (  # for auto generated test names
            name
            if isinstance(name, Name)
            else Name(
                name="NAME",
                value=f"test_t{Test.TEST_COUNT}",
                col_start=name.col_start,
                col_end=name.col_end,
                line=name.line,
                mod_link=mod_link,
                kid=name.kid,
            )
        )
        # kid[0] = self.name  # Index is 0 since Doc string is inserted after init
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class ModuleCode(AstNode):
    """Free mod code for Jac Ast."""

    def __init__(
        self,
        name: Optional[SubTag[Name]],
        body: SubNodeList[CodeBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
        doc: Optional[Constant] = None,
    ) -> None:
        """Initialize test node."""
        self.doc = doc
        self.name = name
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class PyInlineCode(AstNode):
    """Inline Python code node type for Jac Ast."""

    def __init__(
        self,
        code: Token,
        mod_link: Optional[Module],
        kid: list[AstNode],
        doc: Optional[Constant] = None,
    ) -> None:
        """Initialize inline python code node."""
        self.doc = doc
        self.code = code
        super().__init__(mod_link=mod_link, kid=kid)


class Import(AstNode):
    """Import node type for Jac Ast."""

    def __init__(
        self,
        lang: SubTag,
        path: ModulePath,
        alias: Optional[Name],
        items: Optional[SubNodeList[ModuleItem]],
        is_absorb: bool,  # For includes
        mod_link: Optional[Module],
        kid: list[AstNode],
        doc: Optional[Constant] = None,
        sub_module: Optional[Module] = None,
    ) -> None:
        """Initialize import node."""
        self.doc = doc
        self.lang = lang
        self.path = path
        self.alias = alias
        self.items = items
        self.is_absorb = is_absorb
        self.sub_module = sub_module

        super().__init__(mod_link=mod_link, kid=kid)


class ModulePath(AstNode):
    """ModulePath node type for Jac Ast."""

    def __init__(
        self,
        path: list[Token],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize module path node."""
        self.path = path
        self.path_str = "".join([p.value for p in path])
        super().__init__(mod_link=mod_link, kid=kid)


class ModuleItem(AstNode):
    """ModuleItem node type for Jac Ast."""

    def __init__(
        self,
        name: Name,
        alias: Optional[Token],
        mod_link: Optional[Module],
        kid: list[AstNode],
        body: Optional[AstNode] = None,
    ) -> None:
        """Initialize module item node."""
        self.name = name
        self.alias = alias
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class Architype(AstNode):
    """ObjectArch node type for Jac Ast."""

    def __init__(
        self,
        name: Name,
        arch_type: Token,
        access: Optional[SubTag[Token]],
        base_classes: SubNodeList[SubNodeList[NameType]],
        body: Optional[SubNodeList[ArchBlockStmt] | ArchDef],
        mod_link: Optional[Module],
        kid: list[AstNode],
        doc: Optional[Constant] = None,
        decorators: Optional[SubNodeList[ExprType]] = None,
    ) -> None:
        """Initialize object arch node."""
        self.name = name
        self.arch_type = arch_type
        self.doc = doc
        self.decorators = decorators
        self.access = access
        self.base_classes = base_classes
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class ArchDef(AstNode):
    """ArchDef node type for Jac Ast."""

    def __init__(
        self,
        target: ArchRefChain,
        body: SubNodeList[ArchBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
        doc: Optional[Constant] = None,
        decorators: Optional[SubNodeList[ExprType]] = None,
    ) -> None:
        """Initialize arch def node."""
        self.doc = doc
        self.decorators = decorators
        self.target = target
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class Enum(AstNode):
    """Enum node type for Jac Ast."""

    def __init__(
        self,
        name: Name,
        access: Optional[SubTag[Token]],
        base_classes: SubNodeList[SubNodeList[NameType]],
        body: Optional[SubNodeList[EnumBlockStmt] | EnumDef],
        mod_link: Optional[Module],
        kid: list[AstNode],
        doc: Optional[Constant] = None,
        decorators: Optional[SubNodeList[ExprType]] = None,
    ) -> None:
        """Initialize object arch node."""
        self.name = name
        self.doc = doc
        self.access = access
        self.decorators = decorators
        self.base_classes = base_classes
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class EnumDef(AstNode):
    """EnumDef node type for Jac Ast."""

    def __init__(
        self,
        target: ArchRefChain,
        body: SubNodeList[EnumBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
        doc: Optional[Constant] = None,
        decorators: Optional[SubNodeList[ExprType]] = None,
    ) -> None:
        """Initialize arch def node."""
        self.doc = doc
        self.target = target
        self.body = body
        self.decorators = decorators
        super().__init__(mod_link=mod_link, kid=kid)


class Ability(AstNode):
    """Ability node type for Jac Ast."""

    def __init__(
        self,
        name_ref: NameType,
        is_func: bool,
        is_async: bool,
        is_static: bool,
        is_abstract: bool,
        access: Optional[SubTag[Token]],
        signature: Optional[FuncSignature | SubNodeList[TypeSpec] | EventSignature],
        body: Optional[SubNodeList[CodeBlockStmt]],
        mod_link: Optional[Module],
        kid: list[AstNode],
        arch_attached: Optional[Architype] = None,
        doc: Optional[Constant] = None,
        decorators: Optional[SubNodeList[ExprType]] = None,
    ) -> None:
        """Initialize func arch node."""
        self.name_ref = name_ref
        self.is_func = is_func
        self.is_async = is_async
        self.is_static = is_static
        self.is_abstract = is_abstract
        self.doc = doc
        self.decorators = decorators
        self.access = access
        self.signature = signature
        self.body = body
        self.arch_attached = arch_attached
        super().__init__(mod_link=mod_link, kid=kid)

    def py_resolve_name(self) -> str:
        """Resolve name."""
        if isinstance(self.name_ref, Name):
            return self.name_ref.value
        elif isinstance(self.name_ref, (SpecialVarRef, ArchRef)):
            return self.name_ref.py_resolve_name()
        else:
            raise NotImplementedError


class AbilityDef(AstNode):
    """AbilityDef node type for Jac Ast."""

    def __init__(
        self,
        target: ArchRefChain,
        signature: FuncSignature | EventSignature,
        body: SubNodeList[CodeBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
        doc: Optional[Constant] = None,
        decorators: Optional[SubNodeList[ExprType]] = None,
    ) -> None:
        """Initialize ability def node."""
        self.doc = doc
        self.target = target
        self.signature = signature
        self.body = body
        self.decorators = decorators
        super().__init__(mod_link=mod_link, kid=kid)


class EventSignature(AstNode):
    """EventSignature node type for Jac Ast."""

    def __init__(
        self,
        event: Token,
        arch_tag_info: Optional[SubNodeList[TypeSpec]],
        return_type: Optional[SubNodeList[TypeSpec]],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize event signature node."""
        self.event = event
        self.arch_tag_info = arch_tag_info
        self.return_type = return_type
        super().__init__(mod_link=mod_link, kid=kid)


class ArchRefChain(AstNode):
    """Arch ref list node type for Jac Ast."""

    def __init__(
        self,
        archs: list[ArchRef],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize name list ."""
        self.archs = archs
        super().__init__(mod_link=mod_link, kid=kid)

    def py_resolve_name(self) -> str:
        """Resolve name."""
        return ".".join(
            [f"({x.arch.value[1]}){x.py_resolve_name()}" for x in self.archs]
        )


class FuncSignature(AstNode):
    """FuncSignature node type for Jac Ast."""

    def __init__(
        self,
        params: Optional[SubNodeList[ParamVar]],
        return_type: Optional[SubNodeList[TypeSpec]],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize method signature node."""
        self.params = params
        self.return_type = return_type
        super().__init__(mod_link=mod_link, kid=kid)


class ParamVar(AstNode):
    """ParamVar node type for Jac Ast."""

    def __init__(
        self,
        name: Name,
        unpack: Optional[Token],
        type_tag: SubNodeList[TypeSpec],
        value: Optional[ExprType],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize param var node."""
        self.name = name
        self.unpack = unpack
        self.type_tag = type_tag
        self.value = value
        super().__init__(mod_link=mod_link, kid=kid)


class ArchHas(AstNode):
    """HasStmt node type for Jac Ast."""

    def __init__(
        self,
        is_static: bool,
        access: Optional[SubTag[Token]],
        vars: SubNodeList[HasVar],
        is_frozen: bool,
        mod_link: Optional[Module],
        kid: list[AstNode],
        doc: Optional[Constant] = None,
    ) -> None:
        """Initialize has statement node."""
        self.doc = doc
        self.is_static = is_static
        self.vars = vars
        self.access = access
        self.is_frozen = is_frozen
        self.doc = doc
        super().__init__(mod_link=mod_link, kid=kid)


class HasVar(AstNode):
    """HasVar node type for Jac Ast."""

    def __init__(
        self,
        name: Name,
        type_tag: SubTag[SubNodeList[TypeSpec]],
        value: Optional[ExprType],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize has var node."""
        self.name = name
        self.type_tag = type_tag
        self.value = value
        super().__init__(mod_link=mod_link, kid=kid)


class TypeSpec(AstNode):
    """TypeSpec node type for Jac Ast."""

    def __init__(
        self,
        spec_type: Token | SubNodeList[NameType],
        list_nest: Optional[TypeSpec],  # needed for lists
        dict_nest: Optional[TypeSpec],  # needed for dicts, uses list_nest as key
        mod_link: Optional[Module],
        kid: list[AstNode],
        null_ok: bool = False,
    ) -> None:
        """Initialize type spec node."""
        self.spec_type = spec_type
        self.list_nest = list_nest
        self.dict_nest = dict_nest
        self.null_ok = null_ok
        super().__init__(mod_link=mod_link, kid=kid)


class TypedCtxBlock(AstNode):
    """TypedCtxBlock node type for Jac Ast."""

    def __init__(
        self,
        type_ctx: SubNodeList[TypeSpec],
        body: SubNodeList[CodeBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize typed context block node."""
        self.type_ctx = type_ctx
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class IfStmt(AstNode):
    """IfStmt node type for Jac Ast."""

    def __init__(
        self,
        condition: ExprType,
        body: SubNodeList[CodeBlockStmt],
        elseifs: Optional[ElseIfs],
        else_body: Optional[ElseStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize if statement node."""
        self.condition = condition
        self.body = body
        self.elseifs = elseifs
        self.else_body = else_body
        super().__init__(mod_link=mod_link, kid=kid)


class ElseIfs(AstNode):
    """ElseIfs node type for Jac Ast."""

    def __init__(
        self,
        condition: ExprType,
        body: SubNodeList[CodeBlockStmt],
        elseifs: Optional[ElseIfs],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize if statement node."""
        self.condition = condition
        self.body = body
        self.elseifs = elseifs
        super().__init__(mod_link=mod_link, kid=kid)


class ElseStmt(AstNode):
    """Else node type for Jac Ast."""

    def __init__(
        self,
        body: SubNodeList[CodeBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize else node."""
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class TryStmt(AstNode):
    """TryStmt node type for Jac Ast."""

    def __init__(
        self,
        body: SubNodeList[CodeBlockStmt],
        excepts: Optional[SubNodeList[Except]],
        finally_body: Optional[FinallyStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize try statement node."""
        self.body = body
        self.excepts = excepts
        self.finally_body = finally_body
        super().__init__(mod_link=mod_link, kid=kid)


class Except(AstNode):
    """Except node type for Jac Ast."""

    def __init__(
        self,
        ex_type: ExprType,
        name: Optional[Token],
        body: SubNodeList[CodeBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize except node."""
        self.ex_type = ex_type
        self.name = name
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class FinallyStmt(AstNode):
    """FinallyStmt node type for Jac Ast."""

    def __init__(
        self,
        body: SubNodeList[CodeBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize finally statement node."""
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class IterForStmt(AstNode):
    """IterFor node type for Jac Ast."""

    def __init__(
        self,
        iter: Assignment,
        condition: ExprType,
        count_by: ExprType,
        body: SubNodeList[CodeBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize iter for node."""
        self.iter = iter
        self.condition = condition
        self.count_by = count_by
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class InForStmt(AstNode):
    """InFor node type for Jac Ast."""

    def __init__(
        self,
        name_list: SubNodeList[Name],
        collection: ExprType,
        body: SubNodeList[CodeBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize in for node."""
        self.name_list = name_list
        self.collection = collection
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class WhileStmt(AstNode):
    """WhileStmt node type for Jac Ast."""

    def __init__(
        self,
        condition: ExprType,
        body: SubNodeList[CodeBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize while statement node."""
        self.condition = condition
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class WithStmt(AstNode):
    """WithStmt node type for Jac Ast."""

    def __init__(
        self,
        exprs: SubNodeList[ExprAsItem],
        body: SubNodeList[CodeBlockStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize with statement node."""
        self.exprs = exprs
        self.body = body
        super().__init__(mod_link=mod_link, kid=kid)


class ExprAsItem(AstNode):
    """ExprAsItem node type for Jac Ast."""

    def __init__(
        self,
        expr: ExprType,
        alias: Optional[Name],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize module item node."""
        self.expr = expr
        self.alias = alias
        super().__init__(mod_link=mod_link, kid=kid)


class RaiseStmt(AstNode):
    """RaiseStmt node type for Jac Ast."""

    def __init__(
        self,
        cause: Optional[ExprType],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize raise statement node."""
        self.cause = cause
        super().__init__(mod_link=mod_link, kid=kid)


class AssertStmt(AstNode):
    """AssertStmt node type for Jac Ast."""

    def __init__(
        self,
        condition: ExprType,
        error_msg: Optional[ExprType],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize assert statement node."""
        self.condition = condition
        self.error_msg = error_msg
        super().__init__(mod_link=mod_link, kid=kid)


class CtrlStmt(AstNode):
    """CtrlStmt node type for Jac Ast."""

    def __init__(
        self,
        ctrl: Token,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize control statement node."""
        self.ctrl = ctrl
        super().__init__(mod_link=mod_link, kid=kid)


class DeleteStmt(AstNode):
    """DeleteStmt node type for Jac Ast."""

    def __init__(
        self,
        target: ExprType,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize delete statement node."""
        self.target = target
        super().__init__(mod_link=mod_link, kid=kid)


class ReportStmt(AstNode):
    """ReportStmt node type for Jac Ast."""

    def __init__(
        self,
        expr: ExprType,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize report statement node."""
        self.expr = expr
        super().__init__(mod_link=mod_link, kid=kid)


class ReturnStmt(AstNode):
    """ReturnStmt node type for Jac Ast."""

    def __init__(
        self,
        expr: Optional[ExprType],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize return statement node."""
        self.expr = expr
        super().__init__(mod_link=mod_link, kid=kid)


class YieldStmt(AstNode):
    """YieldStmt node type for Jac Ast."""

    def __init__(
        self,
        expr: Optional[ExprType],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize yeild statement node."""
        self.expr = expr
        super().__init__(mod_link=mod_link, kid=kid)


class WalkerStmtOnlyNode(AstNode):
    """WalkerStmtOnlyNode node type for Jac Ast."""

    def __init__(
        self,
        mod_link: Optional[Module],
        kid: list[AstNode],
        from_walker: bool = False,
    ) -> None:
        """Initialize walker statement only node."""
        self.from_walker = from_walker
        super().__init__(mod_link=mod_link, kid=kid)


class IgnoreStmt(WalkerStmtOnlyNode):
    """IgnoreStmt node type for Jac Ast."""

    def __init__(
        self,
        target: ExprType,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize ignore statement node."""
        self.target = target
        super().__init__(mod_link=mod_link, kid=kid)


class VisitStmt(WalkerStmtOnlyNode):
    """VisitStmt node type for Jac Ast."""

    def __init__(
        self,
        vis_type: Optional[SubTag[SubNodeList[Name]]],
        target: ExprType,
        else_body: Optional[ElseStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
        from_walker: bool = False,
    ) -> None:
        """Initialize visit statement node."""
        self.vis_type = vis_type
        self.target = target
        self.else_body = else_body
        super().__init__(
            mod_link=mod_link,
            kid=kid,
            from_walker=from_walker,
        )


class RevisitStmt(WalkerStmtOnlyNode):
    """ReVisitStmt node type for Jac Ast."""

    def __init__(
        self,
        hops: Optional[ExprType],
        else_body: Optional[ElseStmt],
        mod_link: Optional[Module],
        kid: list[AstNode],
        from_walker: bool = False,
    ) -> None:
        """Initialize revisit statement node."""
        self.hops = hops
        self.else_body = else_body
        super().__init__(
            mod_link=mod_link,
            kid=kid,
            from_walker=from_walker,
        )


class DisengageStmt(WalkerStmtOnlyNode):
    """DisengageStmt node type for Jac Ast."""

    def __init__(
        self,
        mod_link: Optional[Module],
        kid: list[AstNode],
        from_walker: bool = False,
    ) -> None:
        """Initialize disengage statement node."""
        super().__init__(
            mod_link=mod_link,
            kid=kid,
            from_walker=from_walker,
        )


class AwaitStmt(AstNode):
    """AwaitStmt node type for Jac Ast."""

    def __init__(
        self,
        target: ExprType,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize sync statement node."""
        self.target = target
        super().__init__(mod_link=mod_link, kid=kid)


class Assignment(AstNode):
    """Assignment node type for Jac Ast."""

    def __init__(
        self,
        target: AtomType,
        value: ExprType,
        mod_link: Optional[Module],
        kid: list[AstNode],
        is_static: bool = False,
        mutable: bool = True,
    ) -> None:
        """Initialize assignment node."""
        self.is_static = is_static
        self.target = target
        self.value = value
        self.mutable = mutable
        super().__init__(mod_link=mod_link, kid=kid)


class IfElseExpr(AstNode):
    """ExprIfElse node type for Jac Ast."""

    def __init__(
        self,
        condition: ExprType,
        value: ExprType,
        else_value: ExprType,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize if else expression node."""
        self.condition = condition
        self.value = value
        self.else_value = else_value
        super().__init__(mod_link=mod_link, kid=kid)


class BinaryExpr(AstNode):
    """ExprBinary node type for Jac Ast."""

    def __init__(
        self,
        left: ExprType,
        right: ExprType,
        op: Constant | DisconnectOp | ConnectOp,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize binary expression node."""
        self.left = left
        self.right = right
        self.op = op
        super().__init__(mod_link=mod_link, kid=kid)


class UnaryExpr(AstNode):
    """ExprUnary node type for Jac Ast."""

    def __init__(
        self,
        operand: ExprType,
        op: Token,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize unary expression node."""
        self.operand = operand
        self.op = op
        super().__init__(mod_link=mod_link, kid=kid)


class MultiString(AstNode):
    """ExprMultiString node type for Jac Ast."""

    def __init__(
        self,
        strings: list[Constant | FString],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize multi string expression node."""
        self.strings = strings
        super().__init__(mod_link=mod_link, kid=kid)


class FString(AstNode):
    """FString node type for Jac Ast."""

    def __init__(
        self,
        parts: Optional[SubNodeList[Constant | ExprType]],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize fstring expression node."""
        self.parts = parts
        super().__init__(mod_link=mod_link, kid=kid)


class ExprList(AstNode):
    """ExprList node type for Jac Ast."""

    def __init__(
        self,
        values: Optional[SubNodeList[ExprType]],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize expr value node."""
        self.values = values
        super().__init__(mod_link=mod_link, kid=kid)


class ListVal(ExprList):
    """ListVal node type for Jac Ast."""


class SetVal(ExprList):
    """SetVal node type for Jac Ast."""


class TupleVal(AstNode):
    """TupleVal node type for Jac Ast."""

    def __init__(
        self,
        values: Optional[SubNodeList[ExprType | Assignment]],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize tuple value node."""
        self.values = values
        super().__init__(mod_link=mod_link, kid=kid)


class DictVal(AstNode):
    """ExprDict node type for Jac Ast."""

    def __init__(
        self,
        kv_pairs: Optional[SubNodeList[KVPair]],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize dict expression node."""
        self.kv_pairs = kv_pairs
        super().__init__(mod_link=mod_link, kid=kid)


class KVPair(AstNode):
    """ExprKVPair node type for Jac Ast."""

    def __init__(
        self,
        key: ExprType,
        value: ExprType,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize key value pair expression node."""
        self.key = key
        self.value = value
        super().__init__(mod_link=mod_link, kid=kid)


class ListCompr(AstNode):
    """ListCompr node type for Jac Ast."""

    def __init__(
        self,
        compr: InnerCompr,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize comprehension expression node."""
        self.compr = compr
        super().__init__(mod_link=mod_link, kid=kid)


class GenCompr(ListCompr):
    """GenCompr node type for Jac Ast."""


class SetCompr(ListCompr):
    """SetCompr node type for Jac Ast."""


class InnerCompr(AstNode):
    """ListCompr node type for Jac Ast."""

    def __init__(
        self,
        out_expr: ExprType,
        names: SubNodeList[Name],
        collection: ExprType,
        conditional: Optional[ExprType],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize comprehension expression node."""
        self.out_expr = out_expr
        self.names = names
        self.collection = collection
        self.conditional = conditional

        super().__init__(mod_link=mod_link, kid=kid)


class DictCompr(AstNode):
    """DictCompr node type for Jac Ast."""

    def __init__(
        self,
        kv_pair: KVPair,
        names: SubNodeList[Name],
        collection: ExprType,
        conditional: Optional[ExprType],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize comprehension expression node."""
        self.kv_pair = kv_pair
        self.names = names
        self.collection = collection
        self.conditional = conditional
        super().__init__(mod_link=mod_link, kid=kid)


class AtomTrailer(AstNode):
    """AtomTrailer node type for Jac Ast."""

    def __init__(
        self,
        target: AtomType,
        right: AtomType,
        null_ok: bool,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize atom trailer expression node."""
        self.target = target
        self.right = right
        self.null_ok = null_ok
        super().__init__(mod_link=mod_link, kid=kid)


class FuncCall(AstNode):
    """FuncCall node type for Jac Ast."""

    def __init__(
        self,
        target: AtomType,
        params: Optional[SubNodeList[ExprType | Assignment]],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize function call expression node."""
        self.target = target
        self.params = params
        super().__init__(mod_link=mod_link, kid=kid)


class IndexSlice(AstNode):
    """IndexSlice node type for Jac Ast."""

    def __init__(
        self,
        start: Optional[ExprType],
        stop: Optional[ExprType],
        is_range: bool,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize index slice expression node."""
        self.start = start
        self.stop = stop
        self.is_range = is_range
        super().__init__(mod_link=mod_link, kid=kid)


class ArchRef(AstNode):
    """ArchRef node type for Jac Ast."""

    def __init__(
        self,
        name_ref: NameType,
        arch: Token,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize architype reference expression node."""
        self.name_ref = name_ref
        self.arch = arch
        super().__init__(mod_link=mod_link, kid=kid)

    def py_resolve_name(self) -> str:
        """Resolve name."""
        if isinstance(self.name_ref, Name):
            return self.name_ref.value
        elif isinstance(self.name_ref, SpecialVarRef):
            return self.name_ref.py_resolve_name()
        else:
            raise NotImplementedError


class SpecialVarRef(AstNode):
    """HereRef node type for Jac Ast."""

    def __init__(
        self,
        var: Token,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize special var reference expression node."""
        self.var = var
        super().__init__(mod_link=mod_link, kid=kid)

    def py_resolve_name(self) -> str:
        """Resolve name."""
        if self.var.name == Tok.SELF_OP:
            return "self"
        elif self.var.name == Tok.SUPER_OP:
            return "super()"
        elif self.var.name == Tok.ROOT_OP:
            return Con.ROOT
        elif self.var.name == Tok.HERE_OP:
            return Con.HERE
        elif self.var.name == Tok.INIT_OP:
            return "__init__"
        else:
            raise NotImplementedError("ICE: Special var reference not implemented")


class EdgeOpRef(WalkerStmtOnlyNode):
    """EdgeOpRef node type for Jac Ast."""

    def __init__(
        self,
        filter_type: Optional[ExprType],
        filter_cond: Optional[FilterCompr],
        edge_dir: EdgeDir,
        mod_link: Optional[Module],
        kid: list[AstNode],
        from_walker: bool = False,
    ) -> None:
        """Initialize edge op reference expression node."""
        self.filter_type = filter_type
        self.filter_cond = filter_cond
        self.edge_dir = edge_dir
        super().__init__(
            mod_link=mod_link,
            kid=kid,
            from_walker=from_walker,
        )


class DisconnectOp(WalkerStmtOnlyNode):
    """DisconnectOpRef node type for Jac Ast."""

    def __init__(
        self,
        edge_spec: EdgeOpRef,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize disconnect op reference expression node."""
        self.edge_spec = edge_spec
        super().__init__(mod_link=mod_link, kid=kid)


class ConnectOp(AstNode):
    """ConnectOpRef node type for Jac Ast."""

    def __init__(
        self,
        conn_type: Optional[ExprType],
        conn_assign: Optional[SubNodeList[Assignment]],
        edge_dir: EdgeDir,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize connect op reference expression node."""
        self.conn_type = conn_type
        self.conn_assign = conn_assign
        self.edge_dir = edge_dir
        super().__init__(mod_link=mod_link, kid=kid)


class FilterCompr(AstNode):
    """FilterCtx node type for Jac Ast."""

    def __init__(
        self,
        compares: SubNodeList[BinaryExpr],
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize filter_cond context expression node."""
        self.compares = compares
        super().__init__(mod_link=mod_link, kid=kid)


# AST Parse-Tree Node Types


# --------------------------
class Parse(AstNode):
    """Parse node type for Jac Ast."""

    def __init__(
        self,
        name: str,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize parse."""
        self.name = name
        super().__init__(mod_link=mod_link, kid=kid)

    def __repr__(self) -> str:
        """Return string representation of parse node."""
        return super().__repr__() + f" ({self.name})" + " line: " + str(self.line)


class Token(AstNode):
    """Token node type for Jac Ast."""

    def __init__(
        self,
        name: str,
        value: str,
        line: int,
        col_start: int,
        col_end: int,
        pos_start: int,
        pos_end: int,
        mod_link: Optional[Module],
        kid: list[AstNode],
    ) -> None:
        """Initialize token."""
        self.name = name
        self.value = value
        self.line_no = line
        self.col_start = col_start
        self.col_end = col_end
        self.pos_start = pos_start
        self.pos_end = pos_end
        super().__init__(mod_link=mod_link, kid=kid)


class Name(Token):
    """Name node type for Jac Ast."""


class Constant(Token):
    """Constant node type for Jac Ast."""


class SourceString(Token):
    """SourceString node type for Jac Ast."""

    def __init__(
        self,
        source: str,
    ) -> None:
        """Initialize source string."""
        super().__init__(
            name="",
            value=source,
            line=0,
            col_start=0,
            col_end=0,
            pos_start=0,
            pos_end=0,
            mod_link=None,
            kid=[],
        )


# ----------------

ArchType = Union[
    Architype,
    ArchDef,
    Enum,
    EnumDef,
]

NameType = Union[
    Name,
    SpecialVarRef,
]

AtomType = Union[
    NameType,
    MultiString,
    ListVal,
    TupleVal,
    SetVal,
    DictVal,
    ListCompr,
    SetCompr,
    GenCompr,
    DictCompr,
    AtomTrailer,
    EdgeOpRef,
    FilterCompr,
    IndexSlice,
    FuncCall,
]

ExprType = Union[
    UnaryExpr,
    BinaryExpr,
    IfElseExpr,
    AtomType,
]

ElementStmt = Union[
    GlobalVars,
    Test,
    ModuleCode,
    Import,
    Architype,
    Ability,
    PyInlineCode,
    Import,
]

ArchBlockStmt = Union[
    Ability,
    Architype,
    ArchHas,
    PyInlineCode,
]

EnumBlockStmt = Union[
    Name,
    Assignment,
    PyInlineCode,
]

CodeBlockStmt = Union[
    Import,
    Architype,
    Ability,
    Assignment,
    ExprType,
    IfStmt,
    IfElseExpr,
    TryStmt,
    IterForStmt,
    InForStmt,
    WhileStmt,
    WithStmt,
    RaiseStmt,
    AssertStmt,
    CtrlStmt,
    DeleteStmt,
    ReportStmt,
    ReturnStmt,
    YieldStmt,
    AwaitStmt,
    DisengageStmt,
    RevisitStmt,
    VisitStmt,
    IgnoreStmt,
    PyInlineCode,
    TypedCtxBlock,
]
# Utiliiy functions
# -----------------


def replace_node(node: AstNode, new_node: Optional[AstNode]) -> AstNode | None:
    """Replace node with new_node."""
    if node.parent:
        node.parent.kid[node.parent.kid.index(node)] = new_node
    if new_node:
        new_node.parent = node.parent
        for i in new_node.kid:
            if i:
                i.parent = new_node
    return new_node


def append_node(
    node: AstNode, new_node: Optional[AstNode], front: bool = False
) -> AstNode | None:
    """Replace node with new_node."""
    if front:
        node.kid.insert(0, new_node)
    else:
        node.kid.append(new_node)
    if new_node:
        new_node.parent = node
    return new_node
