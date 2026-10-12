import json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from aggregate_recommendations import aggregate

def test_cluster_dedup_and_two_picks():
    rows=[]
    for i,(f,b) in enumerate([([1,4,15,27,35],[3,6]),([1,4,15,27,35],[3,6]),([2,7,11,22,31],[2,8])]):
        rows.append({'recommendationId':str(i),'targetDrawNum':'26115','front':f,'back':b,'kind':'exact_5_plus_2','parseConfidence':1,'duplicateCluster':'a' if i<2 else 'b'})
    out=aggregate(rows,'26115'); assert len(out['picks'])==2; assert all(len(x['front'])==5 and len(x['back'])==2 for x in out['picks']); assert out['clusterCount']==2

if __name__ == '__main__':
    test_cluster_dedup_and_two_picks()
    print('aggregate tests passed')
