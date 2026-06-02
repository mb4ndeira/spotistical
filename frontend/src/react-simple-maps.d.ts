declare module "react-simple-maps" {
  import { ComponentType, ReactNode, SVGProps } from "react"

  interface GeographiesProps {
    geography: string
    children: (props: { geographies: GeoFeature[] }) => ReactNode
  }
  interface GeoFeature {
    rsmKey: string
    id: string | number
    properties: Record<string, unknown>
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  type GeographyProps = Record<string, any>
  interface ComposableMapProps {
    projection?: string
    projectionConfig?: Record<string, unknown>
    style?: React.CSSProperties
    children?: ReactNode
  }

  export const ComposableMap: ComponentType<ComposableMapProps>
  export const Geographies: ComponentType<GeographiesProps>
  export const Geography: ComponentType<GeographyProps>
}
