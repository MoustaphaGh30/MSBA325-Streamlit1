import streamlit as st
import pandas as pd
import folium as fl
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import plotly.express as px
import geopandas as gpd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import arabic_reshaper
from bidi.algorithm import get_display



st.title('MSBA 325: Assignment 2, Moustapha Ghandour')
st.write('***')

st.subheader('A Glimpse into the 2022 Lebanese Parliamentary Elections')

st.markdown(':grey[By Clicking on each district\'s name, we can visualize the turnout rate, as well as the voting distributions among each sect.]')

@st.cache_data
def get_gdf():
    sect_df=pd.read_csv('sect_data.csv')
    merged_df=pd.read_csv('district_data.csv')

    #put your own path here
    shapefile_path = 'lbn_admbnda_adm2_cdr_20200810.shp'

    gdf = gpd.read_file(shapefile_path)
    gdf = gdf.applymap(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else x)

    geojson_data = gdf.to_json()

    merged_df['Ratio'] = merged_df['Actual Voters'] / merged_df['Eligible Voters']
    gdf = gdf.merge(merged_df[['area', 'Ratio']], left_on='admin2Name', right_on='area', how='left')
    
    return gdf, merged_df, sect_df


gdf, merged_df, sect_df=get_gdf()


label_offsets = {
    'Tripoli': (-0.1, 0.05),    
    'Zgharta': (-0.04, -0.04), 
    'West Bekaa': (-0.05, 0),   
    'Jezzine': (-0.04, 0.06),
    'Marjaayoun': (-0.06, 0),
    'Beirut': (-0.05, 0.05),       
    'Saida': (-0.05, 0),
    'Nabatieh':(-0.03,0)       
}

@st.cache_data
def create_pie_chart(district_name, eligible_voters, actual_voters):
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.pie(
        [actual_voters, eligible_voters - actual_voters],
        labels=['Actual Voters', 'Rem. Eligible Voters'],
        autopct='%1.1f%%',
        colors=['#66c2a5', '#fc8d62']
    )
    ax.set_title(f'Voting Distribution')

    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close(fig)
    img.seek(0)
    img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')
    return f'<img src="data:image/png;base64,{img_base64}">'


def reshape_and_display_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

@st.cache_data
def create_stacked_bar_chart(district_name, district_data):

    sects = district_data['sect']
    sects= [reshape_and_display_arabic(x) for x in sects]
    eligible_voters = district_data['Eligible Voters']
    actual_voters = district_data['Actual Voters']
    
    non_voters = eligible_voters - actual_voters
    
    fig, ax = plt.subplots(figsize=(2, 2))

    ax.bar(sects, actual_voters, color='b', label='Actual Voters')
    ax.bar(sects, non_voters, bottom=actual_voters, color='gray', label='Non-Voters')
    
    ax.set_xlabel('Sect')
    ax.set_ylabel('Number of Voters')
    ax.set_title(f'{district_name} - Voter Participation by Sect')
    ax.legend(loc='upper right', prop={'size':8})
    
    plt.xticks(rotation=45, ha='right')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    
    img_html = f'<img src="data:image/png;base64,{img_base64}" alt="Bar Chart for {district_name}">'
    
    plt.close(fig)

    return img_html

def create_map():
    m = fl.Map(location=[33.8547, 35.8623], zoom_start=8)

    fl.GeoJson(
        gdf.to_json(),
        name="Districts",
        style_function=lambda feature: {
            'fillColor': '#D2B48C',  
            'color': '#8B4513',  
            'weight': 1,
            'fillOpacity': 1,  
        }
    ).add_to(m)

    for _, row in gdf.iterrows():

        centroid = row.geometry.centroid
        district_name = row["admin2Name"]

        offset_x, offset_y = 0, 0

        #apply custom offsets for district names
        if district_name in label_offsets:
            offset_x, offset_y = label_offsets[district_name]


        district_data = merged_df[merged_df['area'] == district_name]
        sect_data=sect_df[sect_df['district']==district_name]

        if not district_data.empty:
            eligible_voters = district_data['Eligible Voters'].values[0]
            actual_voters = district_data['Actual Voters'].values[0]
            img_html = create_pie_chart(district_name, eligible_voters, actual_voters)
            
        else:
            img_html = f'<div>No data available for pie chart {district_name}</div>'
        
        if not sect_data.empty:    
            bar_html = create_stacked_bar_chart(district_name, sect_data)
        else: 
            bar_html =  f'<div>No data available for stacked bar {district_name}</div>'
        
        combined_html = f'''
            <div style="display: flex; justify-content: space-between;">
                <div style="flex: 1; margin-right: 3px;">
                    {img_html}
                </div>
                <div style="flex: 1; margin-left: 3px;">
                    {bar_html}
                </div>
            </div>
            '''
            
        
        
        popup = fl.Popup(html=combined_html)

        marker = fl.Marker(
            location=[centroid.y + offset_y, centroid.x + offset_x],
            icon=fl.DivIcon(html=f'''
                <div style="font-size: 7pt; color: black;" class="district-label">
                    {district_name.removeprefix('El ')}
                </div>
            ''')
        )
        marker.add_child(popup)  

        marker.add_to(m)
    return m



st.write('***')
m=create_map()
st_folium(m,width=700, height=700)

st.subheader('Insights')
st.markdown(':grey[ 1. Areas closer to the capital are characterized with a better representation across sects, with similar turnout rates for each sect, which indicates that although the turnout rate was low, there was almost equal participation and competition.]')
st.markdown(':grey[2. Areas further from the capital have an inequal distribution of sects, hinting at Lebanon\'s demographic characteristics when it comes to areas further from the capital, which tend to be homogeneous in terms of sectarian representation. In addition, the turnout rates are heavily skewed towards the dominating sect in each district (see Baalbeck, Keserwane).]')
hepatitis=pd.read_csv('Hepatitis.csv')
#making sure there's only one dataset 
hepatitis['dataset'].unique()

#parse the area name : ex: https://dbpedia.org/resource/Beqaa_Valley	becomes Beqaa_Valley
hepatitis['refArea']=[x.split('/')[4] for x in hepatitis['refArea']]
hepatitis['disease']=[x.split('/')[4] for x in hepatitis['disease']]
hepatitis['refPeriod']=pd.to_datetime([x.split('/')[4] for x in hepatitis['refPeriod']])
hepatitis.drop(columns=['dataset','publisher','references','Observation URI'], inplace=True)


st.header('Hepatitis-B Cases in Lebanon: A Time Series View')

st.markdown(':grey[The following visualization views the distribution of hepatitis cases across different Lebanese distritcs, during different timestamps]')

fig = px.bar(hepatitis, x='refArea', y='Number of cases', 
             animation_frame=hepatitis['refPeriod'].dt.strftime('%Y-%m'), 
             title='',
             labels={'refArea': 'Reference Area', 'Number of cases': 'Number of Cases'},
             range_y=[0, hepatitis['Number of cases'].max() + 20]) 

fig.update_layout(xaxis_title='Reference Area', yaxis_title='Number of Cases')

st.plotly_chart(fig)

st.subheader('Insights')
st.markdown(':grey[South Lebanon and Mount Lebanon have ranked relatively higher in terms of the number of hepatitis cases over the years, this could be due to several reasons:]')
st.markdown(':grey[1. Districts that experience higher rates of internal or external migration might be more susceptible to outbreaks, as hepatitis B can be introduced by individuals moving from regions with higher prevalence, we can confirm this hypothesis by combining this with migration data.]')
st.markdown(':grey[2. Some districts may have less access to healthcare services, meaning people may not get vaccinated or treated in time.]')
st.markdown(':grey[3. This is related to the first point, where Hepatitis B can become chronic, and individuals with chronic infections may unknowingly spread the virus. Certain districts, which may already receive new cases in the form of migrations, may lead to the ongoing transmission of the disease, consequently maintaining the high rates within these districts.]')
st.write('***')


