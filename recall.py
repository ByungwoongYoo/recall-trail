import argparse
import json

import relate


def load_demo(connection):
    # Fictional records. The same tagged part moved between two kits.
    connection.execute('''
        MERGE (batch:Batch {id: 'LOT-7'})
        MERGE (other:Batch {id: 'LOT-8'})
        MERGE (part:Part {id: 'P-104'})
        MERGE (safe:Part {id: 'P-105'})
        MERGE (assembly:Assembly {id: 'HEAD-2'})
        MERGE (old:Asset {id: 'KIT-01'})
        MERGE (current:Asset {id: 'KIT-02'})
        MERGE (shelf:Asset {id: 'KIT-03'})
        MERGE (oldLoan:Loan {id: 'LOAN-7'})
        MERGE (liveLoan:Loan {id: 'LOAN-9'})
        MERGE (part)-[:FROM_BATCH]->(batch)
        MERGE (safe)-[:FROM_BATCH]->(other)
        MERGE (part)-[removed:INSTALLED_IN]->(old)
        SET removed.active = false
        MERGE (part)-[mount:INSTALLED_IN]->(assembly)
        SET mount.active = true
        MERGE (assembly)-[inside:INSTALLED_IN]->(current)
        SET inside.active = true
        MERGE (safe)-[unaffected:INSTALLED_IN]->(shelf)
        SET unaffected.active = true
        MERGE (oldLoan)-[returned:CHECKED_OUT]->(current)
        SET returned.active = false
        MERGE (liveLoan)-[checked:CHECKED_OUT]->(current)
        SET checked.active = true
    ''').fetchall()


def trace_batch(connection, batch_id):
    return connection.execute('''
        MATCH (batch:Batch {id: $batchId})<-[:FROM_BATCH]-(part:Part)
        MATCH path = (part)-[:INSTALLED_IN*1..4]->(asset:Asset)
        WHERE all(edge IN relationships(path) WHERE edge.active = true)
        OPTIONAL MATCH (loan:Loan)-[out:CHECKED_OUT]->(asset)
        WHERE out.active = true
        RETURN DISTINCT part.id AS part, asset.id AS asset,
               [item IN nodes(path) | item.id] AS route, loan.id AS loan
        ORDER BY asset, part, loan
    ''', {'batchId': batch_id}).fetchall()


def main():
    parser = argparse.ArgumentParser(description='Trace a part recall through a local Relate database.')
    parser.add_argument('database')
    parser.add_argument('--init-demo', action='store_true')
    parser.add_argument('--batch', default='LOT-7')
    args = parser.parse_args()
    with relate.connect(args.database) as connection:
        if args.init_demo:
            load_demo(connection)
        print(json.dumps(trace_batch(connection, args.batch), indent=2))


if __name__ == '__main__':
    main()
