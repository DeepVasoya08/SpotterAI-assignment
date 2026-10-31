import 'maplibre-gl/dist/maplibre-gl.css'

import { useEffect, useMemo, useRef, useState } from 'react'
import Map, {
  Layer,
  Marker,
  NavigationControl,
  Popup,
  Source,
  type MapLayerMouseEvent,
  type MapRef,
} from 'react-map-gl/maplibre'

import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'

import type { PlannedRoute, TripPlan } from '@/api/types'
import { CheckpointDetails } from '@/features/map/CheckpointDetails'
import { RiskLegend } from '@/features/map/RiskLegend'
import {
  boundsOf,
  checkpointsCollection,
  riskGradient,
  routeFeature,
  routesCollection,
} from '@/features/map/mapData'

const MAP_STYLE = 'https://tiles.openfreemap.org/styles/positron'
// MapLibre finds its worker relative to its own module, which the bundler relocates;
// pointing it at the emitted worker file keeps the map working in dev and production.
const WORKER_URL = maplibreWorkerUrl
const CONTIGUOUS_US_VIEW = { longitude: -98.6, latitude: 39.8, zoom: 3.6 }
const FIT_PADDING = { top: 60, bottom: 60, left: 60, right: 60 }

const ROUTE_HIT_LAYER = 'route-hit'
const CHECKPOINT_LAYER = 'checkpoints'
const INTERACTIVE_LAYERS = [CHECKPOINT_LAYER, ROUTE_HIT_LAYER]

interface TripMapProps {
  plan: TripPlan | null
  selectedRouteId: string | null
  labelOf: (routeId: string) => string
  onSelectRoute: (routeId: string) => void
}

export function TripMap({ plan, selectedRouteId, labelOf, onSelectRoute }: TripMapProps) {
  const mapRef = useRef<MapRef>(null)
  const [cursor, setCursor] = useState('')
  // Tied to the route object, so a new plan or selection closes the popup.
  const [openCheckpoint, setOpenCheckpoint] = useState<{
    route: PlannedRoute
    index: number
  } | null>(null)

  const routes = useMemo(() => plan?.routes ?? [], [plan])
  const selectedRoute = routes.find((route) => route.id === selectedRouteId) ?? null
  const allRoutes = useMemo(() => routesCollection(routes), [routes])
  const selectedLine = useMemo(
    () => (selectedRoute ? routeFeature(selectedRoute) : null),
    [selectedRoute],
  )
  const gradient = useMemo(
    () => (selectedRoute ? riskGradient(selectedRoute) : null),
    [selectedRoute],
  )
  const checkpoints = useMemo(
    () => (selectedRoute ? checkpointsCollection(selectedRoute) : null),
    [selectedRoute],
  )

  useEffect(() => {
    const bounds = boundsOf(routes)
    if (bounds) mapRef.current?.fitBounds(bounds, { padding: FIT_PADDING, duration: 800 })
  }, [routes])

  function handleClick(event: MapLayerMouseEvent) {
    const feature = event.features?.[0]
    if (!feature) {
      setOpenCheckpoint(null)
      return
    }
    if (feature.layer.id === CHECKPOINT_LAYER && selectedRoute) {
      setOpenCheckpoint({ route: selectedRoute, index: Number(feature.properties.index) })
    } else if (feature.layer.id === ROUTE_HIT_LAYER) {
      onSelectRoute(String(feature.properties.id))
    }
  }

  const popupCheckpoint =
    openCheckpoint?.route === selectedRoute
      ? selectedRoute?.checkpoints[openCheckpoint.index]
      : undefined
  const origin = routes[0]?.geometry[0]
  const destination = routes[0]?.geometry.at(-1)

  return (
    <Map
      ref={mapRef}
      initialViewState={CONTIGUOUS_US_VIEW}
      mapStyle={MAP_STYLE}
      workerUrl={WORKER_URL}
      interactiveLayerIds={INTERACTIVE_LAYERS}
      cursor={cursor}
      onMouseEnter={() => setCursor('pointer')}
      onMouseLeave={() => setCursor('')}
      onClick={handleClick}
      style={{ width: '100%', height: '100%' }}
    >
      <NavigationControl position="top-right" showCompass={false} />

      <Source id="routes" type="geojson" data={allRoutes}>
        <Layer
          id="alternative-routes"
          type="line"
          filter={['!=', ['get', 'id'], selectedRouteId ?? '']}
          layout={{ 'line-join': 'round', 'line-cap': 'round' }}
          paint={{ 'line-color': '#64748b', 'line-width': 4, 'line-opacity': 0.55 }}
        />
        <Layer
          id={ROUTE_HIT_LAYER}
          type="line"
          paint={{ 'line-color': '#000000', 'line-width': 18, 'line-opacity': 0 }}
        />
      </Source>

      {selectedLine && gradient && (
        <Source id="selected-route" type="geojson" data={selectedLine} lineMetrics>
          <Layer
            id="selected-route-casing"
            type="line"
            layout={{ 'line-join': 'round', 'line-cap': 'round' }}
            paint={{ 'line-color': '#ffffff', 'line-width': 9 }}
          />
          <Layer
            id="selected-route"
            type="line"
            layout={{ 'line-join': 'round', 'line-cap': 'round' }}
            paint={{ 'line-width': 5, 'line-gradient': gradient }}
          />
        </Source>
      )}

      {checkpoints && (
        <Source id="checkpoints" type="geojson" data={checkpoints}>
          <Layer
            id={CHECKPOINT_LAYER}
            type="circle"
            paint={{
              'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 3, 9, 6],
              'circle-color': ['get', 'color'],
              'circle-stroke-color': '#ffffff',
              'circle-stroke-width': 1.5,
            }}
          />
        </Source>
      )}

      {origin && <EndpointMarker position={origin} label="A" title="Origin" />}
      {destination && <EndpointMarker position={destination} label="B" title="Destination" />}

      {popupCheckpoint && selectedRoute && (
        <Popup
          longitude={popupCheckpoint.lon}
          latitude={popupCheckpoint.lat}
          closeOnClick={false}
          onClose={() => setOpenCheckpoint(null)}
          maxWidth="none"
        >
          <CheckpointDetails checkpoint={popupCheckpoint} routeLabel={labelOf(selectedRoute.id)} />
        </Popup>
      )}

      <RiskLegend />
    </Map>
  )
}

interface EndpointMarkerProps {
  position: [number, number]
  label: string
  title: string
}

function EndpointMarker({ position, label, title }: EndpointMarkerProps) {
  const [longitude, latitude] = position
  return (
    <Marker longitude={longitude} latitude={latitude} anchor="center">
      <span
        title={title}
        className="grid size-7 place-items-center rounded-full border-2 border-white bg-slate-900 text-xs font-bold text-white shadow-md"
      >
        {label}
      </span>
    </Marker>
  )
}
