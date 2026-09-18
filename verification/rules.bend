# Stable framework rules. Application behavior never belongs in this module.
import Base

type PackageKind is Data:
  Brick{}
  Workflow{}

type Lane is Data:
  Strict{}
  Pure{}

type ImportRole is Data:
  Adapter{}
  Flow{}
  Other{}

type ImportSurface is Data:
  Entry{}
  Contract{}
  Internal{}
  External{}

type Package is Data:
  Package{
    id: U32,
    kind: PackageKind,
    lane: Lane,
    rank: U32,
    dependencies: List<&2, U32>,
    shape_valid: Bool
  }

type ImportEdge is Data:
  ImportEdge{
    source: U32,
    target: U32,
    role: ImportRole,
    surface: ImportSurface
  }

type StateOwner is Data:
  StateOwner{resource: U32, owner: U32}

type Repository is Data:
  Repository{
    packages: List<&2, Package>,
    imports: List<&2, ImportEdge>,
    state: List<&2, StateOwner>
  }

def kind_is_brick(kind: PackageKind) -> Bool:
  match kind:
    case Brick{}:
      True{}
    case Workflow{}:
      False{}

def lane_allows_dependencies(lane: Lane, dependencies: List<&2, U32>) -> Bool:
  match lane:
    case Strict{}:
      True{}
    case Pure{}:
      List.is_empty(&2, U32, dependencies)

def package_target_valid(
  +target: U32,
  +source_rank: U32,
  packages: List<&2, Package>
) -> Bool:
  match packages:
    case Nil{}:
      False{}
    case Package{id, kind, lane, rank, dependencies, shape_valid} <> rest:
      Bool.or(
        Bool.and(
          U32.is_eq(id, target),
          Bool.and(kind_is_brick(kind), U32.is_lt(rank, source_rank))
        ),
        package_target_valid(target, source_rank, rest)
      )

def has_import(+source: U32, +target: U32, imports: List<&2, ImportEdge>) -> Bool:
  match imports:
    case Nil{}:
      False{}
    case ImportEdge{edge_source, edge_target, role, surface} <> rest:
      Bool.or(
        Bool.and(U32.is_eq(source, edge_source), U32.is_eq(target, edge_target)),
        has_import(source, target, rest)
      )

def dependencies_valid(
  +source: U32,
  +source_rank: U32,
  dependencies: List<&2, U32>,
  +packages: List<&2, Package>,
  +imports: List<&2, ImportEdge>
) -> Bool:
  match dependencies:
    case Nil{}:
      True{}
    case +target <> rest:
      Bool.and(
        Bool.and(
          package_target_valid(target, source_rank, packages),
          has_import(source, target, imports)
        ),
        dependencies_valid(source, source_rank, rest, packages, imports)
      )

def package_id_absent(+id: U32, packages: List<&2, Package>) -> Bool:
  match packages:
    case Nil{}:
      True{}
    case Package{other, kind, lane, rank, dependencies, shape_valid} <> rest:
      Bool.and(U32.is_ne(id, other), package_id_absent(id, rest))

def package_ids_unique(packages: List<&2, Package>) -> Bool:
  match packages:
    case Nil{}:
      True{}
    case Package{id, kind, lane, rank, dependencies, shape_valid} <> +rest:
      Bool.and(package_id_absent(id, rest), package_ids_unique(rest))

def packages_valid(
  packages: List<&2, Package>,
  +all_packages: List<&2, Package>,
  +imports: List<&2, ImportEdge>
) -> Bool:
  match packages:
    case Nil{}:
      True{}
    case Package{id, kind, lane, rank, +dependencies, shape_valid} <> rest:
      Bool.and(
        Bool.and(
          shape_valid,
          Bool.and(
            lane_allows_dependencies(lane, dependencies),
            dependencies_valid(id, rank, dependencies, all_packages, imports)
          )
        ),
        packages_valid(rest, all_packages, imports)
      )

def dependency_declared(+source: U32, +target: U32, packages: List<&2, Package>) -> Bool:
  match packages:
    case Nil{}:
      False{}
    case Package{id, kind, lane, rank, dependencies, shape_valid} <> rest:
      Bool.or(
        Bool.and(
          U32.is_eq(id, source),
          List.contains(~U32, ~U32.is_eq, dependencies, target)
        ),
        dependency_declared(source, target, rest)
      )

def target_is_brick(+target: U32, packages: List<&2, Package>) -> Bool:
  match packages:
    case Nil{}:
      False{}
    case Package{id, kind, lane, rank, dependencies, shape_valid} <> rest:
      Bool.or(
        Bool.and(U32.is_eq(id, target), kind_is_brick(kind)),
        target_is_brick(target, rest)
      )

def role_is_adapter(role: ImportRole) -> Bool:
  match role:
    case Adapter{}:
      True{}
    case Flow{}:
      False{}
    case Other{}:
      False{}

def lane_allows_external(lane: Lane) -> Bool:
  match lane:
    case Strict{}:
      True{}
    case Pure{}:
      False{}

def source_allows_external(+source: U32, +role: ImportRole, packages: List<&2, Package>) -> Bool:
  match packages:
    case Nil{}:
      False{}
    case Package{id, kind, lane, rank, dependencies, shape_valid} <> rest:
      Bool.or(
        Bool.and(
          U32.is_eq(id, source),
          Bool.and(
            kind_is_brick(kind),
            Bool.and(lane_allows_external(lane), role_is_adapter(role))
          )
        ),
        source_allows_external(source, role, rest)
      )

def surface_is_entry(surface: ImportSurface) -> Bool:
  match surface:
    case Entry{}:
      True{}
    case Contract{}:
      False{}
    case Internal{}:
      False{}
    case External{}:
      False{}

def surface_is_public(surface: ImportSurface) -> Bool:
  match surface:
    case Entry{}:
      True{}
    case Contract{}:
      True{}
    case Internal{}:
      False{}
    case External{}:
      False{}

def kind_allows_import(kind: PackageKind, role: ImportRole, surface: ImportSurface) -> Bool:
  match kind:
    case Brick{}:
      match role:
        case Adapter{}:
          surface_is_entry(surface)
        case Flow{}:
          False{}
        case Other{}:
          False{}
    case Workflow{}:
      match role:
        case Adapter{}:
          False{}
        case Flow{}:
          surface_is_public(surface)
        case Other{}:
          False{}

def package_import_role_valid(
  +source: U32,
  +role: ImportRole,
  +surface: ImportSurface,
  packages: List<&2, Package>
) -> Bool:
  match packages:
    case Nil{}:
      False{}
    case Package{id, kind, lane, rank, dependencies, shape_valid} <> rest:
      Bool.or(
        Bool.and(
          U32.is_eq(id, source),
          kind_allows_import(kind, role, surface)
        ),
        package_import_role_valid(source, role, surface, rest)
      )

def import_valid(edge: ImportEdge, +packages: List<&2, Package>) -> Bool:
  match edge:
    case ImportEdge{+source, +target, +role, surface}:
      match surface:
        case External{}:
          source_allows_external(source, role, packages)
        case Entry{}:
          Bool.and(
            Bool.and(target_is_brick(target, packages), dependency_declared(source, target, packages)),
            package_import_role_valid(source, role, Entry{}, packages)
          )
        case Contract{}:
          Bool.and(
            Bool.and(target_is_brick(target, packages), dependency_declared(source, target, packages)),
            package_import_role_valid(source, role, Contract{}, packages)
          )
        case Internal{}:
          False{}

def imports_valid(imports: List<&2, ImportEdge>, +packages: List<&2, Package>) -> Bool:
  match imports:
    case Nil{}:
      True{}
    case edge <> rest:
      Bool.and(import_valid(edge, packages), imports_valid(rest, packages))

def resource_absent(+resource: U32, state: List<&2, StateOwner>) -> Bool:
  match state:
    case Nil{}:
      True{}
    case StateOwner{other, owner} <> rest:
      Bool.and(U32.is_ne(resource, other), resource_absent(resource, rest))

def owner_is_brick(+owner: U32, packages: List<&2, Package>) -> Bool:
  target_is_brick(owner, packages)

def state_valid(state: List<&2, StateOwner>, +packages: List<&2, Package>) -> Bool:
  match state:
    case Nil{}:
      True{}
    case StateOwner{resource, owner} <> +rest:
      Bool.and(
        Bool.and(resource_absent(resource, rest), owner_is_brick(owner, packages)),
        state_valid(rest, packages)
      )

def validate(repository: Repository) -> Bool:
  match repository:
    case Repository{+packages, +imports, state}:
      Bool.and(
        package_ids_unique(packages),
        Bool.and(
          packages_valid(packages, packages, imports),
          Bool.and(imports_valid(imports, packages), state_valid(state, packages))
        )
      )
