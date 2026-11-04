//  date/number formatters

export const buildingName = (filename: string) =>
  filename.replace(/\.(ifc|ifczip|ifcxml)$/i, '').replace(/[_-]+/g, ' ');
